"""Profile-backed AWS SDK adapters with an optional local emulator mode."""
import json
import os
import time
import threading
from urllib.parse import urlparse
import boto3
import httpx
from botocore.config import Config
from . import platform_store as ledger
from . import cloud_budget
from .storage import setting, set_setting, utcnow

_queue_lock = threading.Lock()

def writes_enabled():
    return service_mode() == 'local' or os.getenv('ATMOS_AWS_ALLOW_WRITES', 'false').lower() == 'true'

def service_mode():
    return os.getenv('ATMOS_AWS_MODE','local' if os.getenv('ATMOS_AWS_ENDPOINT') else 'disabled')

def configured():
    return service_mode()=='aws' or (service_mode()=='local' and bool(endpoint()))

def aws_session():
    session = boto3.Session(profile_name=os.getenv('AWS_PROFILE') or None,region_name=os.getenv('AWS_REGION','ap-south-1'))
    expected = os.getenv('ATMOS_EXPECTED_AWS_ACCOUNT')
    if expected:
        identity = session.client('sts',config=Config(connect_timeout=3,read_timeout=10,retries={'total_max_attempts':1})).get_caller_identity()
        if identity['Account']!=expected:
            raise ValueError('AWS profile account does not match ATMOS_EXPECTED_AWS_ACCOUNT')
    return session

class MeteredClient:
    def __init__(self,inner,service):
        self.inner,self.service = inner,service
    def __getattr__(self,name):
        target = getattr(self.inner,name)
        if not callable(target):
            return target
        def invoke(*args,**kwargs):
            cloud_budget.reserve(self.service)
            return target(*args,**kwargs)
        return invoke

def require_writes():
    if service_mode()=='aws' and os.getenv('ATMOS_AWS_ALLOW_WRITES','false').lower()!='true':
        raise ValueError('AWS writes are off. Review resources, permissions and costs before enabling ATMOS_AWS_ALLOW_WRITES.')

def endpoint():
    value = os.getenv('ATMOS_AWS_ENDPOINT','')
    if not value:
        return None
    if urlparse(value).hostname not in ('localhost','127.0.0.1','::1'):
        raise ValueError('Build It AWS adapters require a local emulator endpoint')
    return value

def client(service):
    if service_mode()=='aws':
        return MeteredClient(aws_session().client(service,config=Config(connect_timeout=3,read_timeout=15,retries={'total_max_attempts':1})),service)
    if service_mode()!='local':
        raise ValueError('AWS services are disabled; choose profile-backed aws or local mode')
    url = endpoint()
    if not url:
        raise ValueError('Configure ATMOS_AWS_ENDPOINT for local AWS APIs')
    return boto3.client(service,endpoint_url=url,region_name='us-east-1',aws_access_key_id='atmos-local',aws_secret_access_key='atmos-local',
        config=Config(connect_timeout=2,read_timeout=5,retries={'max_attempts':1},s3={'addressing_style':'path'}))

def names():
    resources = {'bucket':os.getenv('ATMOS_S3_BUCKET') or 'atmos-evidence','table':os.getenv('ATMOS_DYNAMODB_TABLE') or 'atmos-runs','queue':os.getenv('ATMOS_SQS_QUEUE') or 'atmos-analysis'}
    if service_mode()=='aws' and any(not os.getenv(key) for key in ('ATMOS_S3_BUCKET','ATMOS_DYNAMODB_TABLE','ATMOS_SQS_QUEUE')):
        raise ValueError('Set cloud resource names from the reviewed CloudFormation stack outputs')
    return resources

def bootstrap():
    if service_mode()=='aws':
        raise ValueError('Create cloud resources from infra/cloud.yaml after reviewing the stack. App bootstrap is for local emulators only.')
    resources = names()
    s3 = client('s3')
    if resources['bucket'] not in [item['Name'] for item in s3.list_buckets()['Buckets']]:
        s3.create_bucket(Bucket=resources['bucket'])
    dynamo = client('dynamodb')
    if resources['table'] not in dynamo.list_tables()['TableNames']:
        dynamo.create_table(TableName=resources['table'],KeySchema=[{'AttributeName':'id','KeyType':'HASH'}],
            AttributeDefinitions=[{'AttributeName':'id','AttributeType':'S'}],BillingMode='PAY_PER_REQUEST')
    queue = client('sqs').create_queue(QueueName=resources['queue'])['QueueUrl']
    ledger.audit('aws.local.bootstrap','local-emulator',resources)
    return dict(resources,queue_url=queue,emulated=True)

def publish(run_id,artifact_id):
    require_writes()
    run = ledger.get_run(run_id)
    document = ledger.artifact(artifact_id)
    raw = json.dumps(document,allow_nan=False).encode()
    if len(raw)>2000000:
        raise ValueError('Evidence object exceeds the 2 MB cloud upload limit')
    resources = names()
    client('s3').put_object(Bucket=resources['bucket'],Key=f"{run['mode']}/{artifact_id}.json",Body=raw,ContentType='application/json')
    client('dynamodb').put_item(TableName=resources['table'],Item={'id':{'S':run_id},'mode':{'S':run['mode']},'city_id':{'S':run['city_id']},'status':{'S':run['status']},'artifact_id':{'S':artifact_id},'updated_at':{'S':run['updated_at']},'expires_at':{'N':str(int(time.time())+30*86400)}})
    with ledger.connect() as db:
        db.execute('UPDATE artifacts SET delivery=? WHERE id=?',('S3 AWS' if service_mode()=='aws' else 'S3 local emulator',artifact_id))
    ledger.audit('aws.publish',artifact_id,{'bucket':resources['bucket'],'mode':service_mode()})
    return {'bucket':resources['bucket'],'key':f"{run['mode']}/{artifact_id}.json",'emulated':service_mode()!='aws'}

def publish_simulation(result):
    require_writes()
    resources = names()
    key = f"simulations/{result['mode']}/{result['id']}.json"
    raw = json.dumps(result, allow_nan=False).encode()
    if len(raw) > 2000000:
        raise ValueError('Simulation report exceeds the 2 MB cloud upload limit')
    client('s3').put_object(Bucket=resources['bucket'], Key=key, Body=raw, ContentType='application/json')
    client('dynamodb').put_item(TableName=resources['table'], Item={
        'id': {'S': result['id']}, 'kind': {'S': 'simulation'}, 'name': {'S': result['name']},
        'mode': {'S': result['mode']}, 'city_id': {'S': result['city_id']}, 'status': {'S': 'complete'},
        'artifact_key': {'S': key}, 'updated_at': {'S': result['created_at']},
        'expires_at': {'N': str(int(time.time()) + 30 * 86400)}})
    record_metric('SimulationCompleted', 1, 'Count')
    return {'status': 'published', 'bucket': resources['bucket'], 'key': key,
            'services': ['S3', 'DynamoDB'], 'emulated': service_mode() != 'aws'}

def record_metric(name, value, unit='Count'):
    if service_mode() != 'aws' or not writes_enabled() or os.getenv('ATMOS_CLOUDWATCH_ENABLED', 'false').lower() != 'true':
        return
    try:
        client('cloudwatch').put_metric_data(Namespace='Atmos/SmokeTwin',
            MetricData=[{'MetricName': name, 'Value': value, 'Unit': unit}])
    except Exception:
        # Metrics are optional; evidence storage and local work remain available.
        pass

def enqueue(run_id):
    require_writes()
    sqs = client('sqs')
    queue = sqs.get_queue_url(QueueName=names()['queue'])['QueueUrl']
    result = sqs.send_message(QueueUrl=queue,MessageBody=json.dumps({'run_id':run_id}),MessageAttributes={'mode':{'DataType':'String','StringValue':ledger.get_run(run_id)['mode']}})
    return {'message_id':result['MessageId'],'emulated':service_mode()!='aws'}

def consume_one():
    require_writes()
    from .analysis import execute
    sqs = client('sqs')
    queue = sqs.get_queue_url(QueueName=names()['queue'])['QueueUrl']
    response = sqs.receive_message(QueueUrl=queue,MaxNumberOfMessages=1,WaitTimeSeconds=1,VisibilityTimeout=300)
    if not response.get('Messages'):
        return {'processed':False}
    item = response['Messages'][0]
    run_id = json.loads(item['Body'])['run_id']
    execute(run_id) # atomic ledger claim prevents duplicate SDK execution
    sqs.delete_message(QueueUrl=queue,ReceiptHandle=item['ReceiptHandle'])
    return {'processed':True,'run_id':run_id}

def drain_pending():
    # A bounded worker wakes only when an analysis is enqueued: no endless idle polling.
    with _queue_lock:
        for _ in range(10):
            if not consume_one()['processed']:
                break

def search_url():
    value = os.getenv('ATMOS_OPENSEARCH_URL','')
    if value and urlparse(value).hostname not in ('localhost','127.0.0.1','::1'):
        raise ValueError('Build It OpenSearch must use a local endpoint')
    return value

def index_evidence():
    url = search_url()
    if not url:
        raise ValueError('Set ATMOS_OPENSEARCH_URL to enable OpenSearch')
    with httpx.Client(timeout=15) as http:
        response = http.put(url+'/atmos-evidence',json={'mappings':{'properties':{'mode':{'type':'keyword'},'city_id':{'type':'keyword'},'title':{'type':'text'},'body':{'type':'text'}}}})
        if response.status_code not in (200,201) and 'resource_already_exists_exception' not in response.text:
            response.raise_for_status()
        count = 0
        for item in ledger.artifacts():
            document = ledger.artifact(item['id'])
            result = http.put(url+'/atmos-evidence/_doc/'+item['id'],params={'refresh':'wait_for'},json={'mode':item['mode'],'city_id':item['city_id'],'title':item['title'],'body':json.dumps(document['payload'])})
            result.raise_for_status()
            count += 1
    return {'indexed':count,'engine':'OpenSearch'}

def retrieve(query,mode,city_id=None):
    url = search_url()
    if not url:
        return {'engine':'SQLite FTS5','results':ledger.search(query,mode,city_id)}
    filters = [{'term':{'mode':mode}}]
    if city_id:
        filters.append({'term':{'city_id':city_id}})
    try:
        with httpx.Client(timeout=5) as http:
            response = http.post(url+'/atmos-evidence/_search',json={'size':10,'query':{'bool':{'must':[{'multi_match':{'query':query,'fields':['title','body']}}],'filter':filters}},'highlight':{'fields':{'body':{}}}})
            response.raise_for_status()
            hits = response.json()['hits']['hits']
        return {'engine':'OpenSearch','results':[{'id':hit['_id'],'title':hit['_source']['title'],'excerpt':' '.join(hit.get('highlight',{}).get('body',[]))[:1000]} for hit in hits]}
    except Exception as exc:
        return {'engine':'SQLite FTS5 fallback','error':type(exc).__name__,'results':ledger.search(query,mode,city_id)}

def status():
    return {'build_mode':'Build It','aws_open_source':['Strands Agents SDK','OpenSearch (optional local service)','AWS SAM (optional local function)'],
        'service_mode':service_mode(),'profile':os.getenv('AWS_PROFILE') or 'default','region':os.getenv('AWS_REGION',os.getenv('ATMOS_HOSTING_REGION','us-east-1')),
        'aws_configured':configured(),'writes_enabled':os.getenv('ATMOS_AWS_ALLOW_WRITES','false').lower()=='true',
        'local_aws_configured':bool(os.getenv('ATMOS_AWS_ENDPOINT')),'opensearch_configured':bool(os.getenv('ATMOS_OPENSEARCH_URL')),
        'queue_enabled':os.getenv('ATMOS_ANALYSIS_QUEUE','local')=='sqs','cloud_deployed':os.getenv('ATMOS_HOSTING')=='ec2',
        'services':['S3 evidence artifacts','DynamoDB run metadata','SQS analysis queue','CloudWatch application metrics'],
        'inventory': service_inventory(),
        'note':'Configured services are not marked connected until a successful connection check. Strands is an SDK, not a hosted AWS service.'}

def service_inventory():
    hosted = os.getenv('ATMOS_HOSTING') == 'ec2'
    checks = setting('aws_connection_check', {})
    def state(name, enabled=True):
        if not configured() or not enabled:
            return 'not_configured'
        return 'connected' if checks.get('checks', {}).get(name, {}).get('status') == 'connected' else 'configured'
    return [
        {'name': 'Amazon EC2', 'status': 'active' if hosted else 'local', 'purpose': 'Runs FastAPI, React and the simulation worker.', 'kind': 'AWS service'},
        {'name': 'Amazon EBS', 'status': 'active' if hosted else 'local', 'purpose': 'Persistent SQLite data, saved runs and models on the EC2 volume.', 'kind': 'AWS service'},
        {'name': 'Amazon VPC', 'status': 'active' if hosted else 'local', 'purpose': 'Instance network and security groups; the app backend listens on loopback behind HTTPS.', 'kind': 'AWS service'},
        {'name': 'AWS Strands Agents SDK', 'status': 'integrated', 'purpose': 'Orchestrates the five analysis specialists.', 'kind': 'Open source SDK'},
        {'name': 'Amazon S3', 'status': state('S3'), 'purpose': 'Private JSON evidence and simulation reports.', 'kind': 'AWS service'},
        {'name': 'Amazon DynamoDB', 'status': state('DynamoDB'), 'purpose': 'Run metadata and report pointers; 30-day TTL.', 'kind': 'AWS service'},
        {'name': 'Amazon SQS', 'status': state('SQS', os.getenv('ATMOS_ANALYSIS_QUEUE') == 'sqs'), 'purpose': 'Queued specialist analysis with a bounded worker and dead-letter queue.', 'kind': 'AWS service'},
        {'name': 'Amazon CloudWatch', 'status': state('CloudWatch', os.getenv('ATMOS_CLOUDWATCH_ENABLED') == 'true'), 'purpose': 'Simulation completion and analysis duration metrics.', 'kind': 'AWS service'},
        {'name': 'AWS CloudFormation', 'status': 'provisioned' if os.getenv('ATMOS_CLOUDFORMATION_STACK') else 'template_ready', 'purpose': 'Provisions the private storage, queues, logs and EC2 application role.', 'kind': 'AWS service'},
        {'name': 'AWS IAM', 'status': 'configured' if os.getenv('ATMOS_AWS_MODE') == 'aws' and hosted else 'template_ready', 'purpose': 'Scoped EC2 application role with temporary credentials; account activation and role attachment required.', 'kind': 'AWS service'},
        {'name': 'Amazon Bedrock', 'status': 'configured' if os.getenv('ATMOS_AGENT_PROVIDER') == 'bedrock' else 'not_enabled', 'purpose': 'Optional paid language-model reasoning; current analysis uses a local rule router.', 'kind': 'AWS service'},
    ]

def connection_check():
    resources = names()
    checks = {}
    for name,call in [('S3',lambda:client('s3').head_bucket(Bucket=resources['bucket'])),
        ('DynamoDB',lambda:client('dynamodb').describe_table(TableName=resources['table'])),
        ('SQS',lambda:client('sqs').get_queue_url(QueueName=resources['queue']))]:
        try:
            call();checks[name] = {'status':'connected'}
        except Exception as exc:
            checks[name] = {'status':'failed','error':type(exc).__name__}
    if os.getenv('ATMOS_CLOUDWATCH_ENABLED') == 'true':
        try:
            require_writes()
            # Do not infer connectivity from the best-effort metric helper.
            client('cloudwatch').put_metric_data(Namespace='Atmos/SmokeTwin', MetricData=[{'MetricName':'ConnectionCheck','Value':1,'Unit':'Count'}])
            checks['CloudWatch'] = {'status': 'connected'}
        except Exception as exc:
            checks['CloudWatch'] = {'status': 'failed', 'error': type(exc).__name__}
    result = {'mode':service_mode(),'checks':checks,'checked_at':utcnow(),'provisioned':False}
    set_setting('aws_connection_check', result)
    return result
