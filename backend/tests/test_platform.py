import importlib.util
import json
from pathlib import Path
import pytest
from backend import platform_store as ledger, analysis, aws_services

def run_request():
    return {'mode':'demo','city_id':'delhi','horizon':6,'audience':'principal','multiplier':2,'session_id':'platform-check','message':'Compare the scenario and create a school plan'}

def test_actual_strands_graph_durable_evidence_and_actions(client,monkeypatch):
    monkeypatch.setenv('ATMOS_AWS_MODE','disabled')
    run = ledger.create_run(run_request())
    finished = analysis.execute(run['id'])
    assert finished['status']=='complete',finished['error']
    evidence = finished['result']
    assert set(evidence['agents'])=={'intelligence','forecast','scenario','impact','strategy'}
    assert evidence['framework']=='AWS Strands Graph'
    assert evidence['agents']['scenario']['inputs']['fire_multiplier']==2
    events = ledger.events(run['id'])
    assert len([event for event in events if event['kind']=='tool_completed'])==5
    assert events[-1]['kind']=='complete'
    assert len(evidence['action_ids'])==3
    assert ledger.artifact(evidence['artifact_id'])['mode']=='demo'
    assert ledger.search('school','demo','delhi')
    assert not ledger.search('school','live','delhi')
    # An already-claimed/completed queue message cannot execute tools twice.
    assert analysis.execute(run['id'])['result']==evidence
    assert len(ledger.events(run['id']))==len(events)
    response = client.patch('/api/actions/'+evidence['action_ids'][0],json={'status':'accepted'})
    assert response.status_code==200
    stream = client.get('/api/runs/'+run['id']+'/events').text
    assert 'tool_completed' in stream and 'complete' in stream
    assert client.get('/api/runs/'+run['id']).json()['result']['artifact_id']==evidence['artifact_id']

def test_run_and_job_restart_recovery(client):
    run = ledger.create_run(run_request())
    ledger.save_job({'id':'restart-check','name':'example','status':'running'})
    ledger.recover()
    assert ledger.get_run(run['id'])['status']=='interrupted'
    assert ledger.get_job('restart-check')['status']=='interrupted'

def test_cloud_write_and_resource_creation_gates(monkeypatch):
    monkeypatch.setenv('ATMOS_AWS_MODE','aws')
    monkeypatch.setenv('ATMOS_AWS_ALLOW_WRITES','false')
    with pytest.raises(ValueError,match='writes are off'):
        aws_services.require_writes()
    with pytest.raises(ValueError,match='infra/cloud.yaml'):
        aws_services.bootstrap()
    monkeypatch.setenv('ATMOS_AWS_MODE','local')
    monkeypatch.setenv('ATMOS_AWS_ENDPOINT','https://aws.example.invalid')
    with pytest.raises(ValueError,match='local emulator'):
        aws_services.client('s3')

def test_aws_s3_dynamodb_sqs_and_lambda_manifest(client,monkeypatch):
    moto = pytest.importorskip('moto',reason='Optional AWS emulator integration dependency')
    monkeypatch.setenv('ATMOS_AWS_MODE','local')
    monkeypatch.setenv('ATMOS_AWS_ENDPOINT','http://localhost:5000')
    # SDK requests use moto's in-process AWS implementation, not a cloud account.
    def mock_client(service):
        import boto3
        return boto3.client(service,region_name='us-east-1',aws_access_key_id='test',aws_secret_access_key='test')
    monkeypatch.setattr(aws_services,'client',mock_client)
    for name in ('ATMOS_S3_BUCKET','ATMOS_DYNAMODB_TABLE','ATMOS_SQS_QUEUE'):
        monkeypatch.delenv(name,raising=False)
    with moto.mock_aws():
        resources = aws_services.bootstrap()
        assert resources['emulated']
        run = ledger.create_run(run_request())
        finished = analysis.execute(run['id'])
        assert finished['status']=='complete',finished['error']
        assert finished['result']['aws_delivery']['emulated']
        artifact_id = finished['result']['artifact_id']
        key = 'demo/'+artifact_id+'.json'
        body = mock_client('s3').get_object(Bucket='atmos-evidence',Key=key)['Body'].read()
        assert json.loads(body)['run_id']==run['id']
        metadata = mock_client('dynamodb').get_item(TableName='atmos-runs',Key={'id':{'S':run['id']}})['Item']
        assert metadata['artifact_id']['S']==artifact_id
        queued = ledger.create_run(run_request())
        assert aws_services.enqueue(queued['id'])['message_id']
        assert aws_services.consume_one()['processed']
        assert ledger.get_run(queued['id'])['status']=='complete'
        assert not aws_services.consume_one()['processed']
        # The SAM handler runs against the same emulated S3 object.
        spec = importlib.util.spec_from_file_location('manifest_handler',Path(__file__).resolve().parents[2]/'infra/manifest/handler.py')
        handler = importlib.util.module_from_spec(spec);spec.loader.exec_module(handler)
        s3_client = mock_client('s3')
        monkeypatch.setattr(handler.boto3,'client',lambda *args,**kwargs:s3_client)
        manifest = handler.handler({'key':key},None)
        assert manifest['framework']=='AWS Strands Graph'
        assert len(manifest['sha256'])==64
        assert len(manifest['specialists'])==5

def test_opensearch_mode_and_city_filter(client,monkeypatch):
    import httpx
    seen=[]
    def respond(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200,json={'hits':{'hits':[{'_id':'evidence-one','_source':{'title':'Delhi outlook'},'highlight':{'body':['school evidence']}}]}})
    original = httpx.Client
    monkeypatch.setenv('ATMOS_OPENSEARCH_URL','http://localhost:9200')
    monkeypatch.setattr(aws_services.httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(respond)))
    result = aws_services.retrieve('school','demo','delhi')
    assert result['engine']=='OpenSearch'
    assert seen[0]['query']['bool']['filter']==[{'term':{'mode':'demo'}},{'term':{'city_id':'delhi'}}]
