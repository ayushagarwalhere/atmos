"""SAM local function: verify an Atmos evidence object stored in local S3."""
import hashlib
import json
import os
from urllib.parse import urlparse
import boto3
from botocore.config import Config

def handler(event,context):
    endpoint = os.getenv('ATMOS_AWS_ENDPOINT','http://host.docker.internal:5000')
    if urlparse(endpoint).hostname not in ('localhost','127.0.0.1','host.docker.internal'):
        raise ValueError('Use a local emulator endpoint for this Build It function')
    key = event['key']
    if '..' in key or not key.endswith('.json') or not key.startswith(('demo/','live/')):
        raise ValueError('Expected a demo/ or live/ evidence JSON key')
    s3 = boto3.client('s3',endpoint_url=endpoint,region_name='us-east-1',aws_access_key_id='atmos-local',aws_secret_access_key='atmos-local',config=Config(s3={'addressing_style':'path'}))
    response = s3.get_object(Bucket='atmos-evidence',Key=key)
    raw = response['Body'].read()
    document = json.loads(raw)
    evidence = document['payload']
    return {'key':key,'sha256':hashlib.sha256(raw).hexdigest(),'mode':document['mode'],
        'city_id':document['city_id'],'run_id':document['run_id'],
        'specialists':sorted(evidence['agents']),'synthetic':evidence['synthetic'],
        'framework':evidence['framework'],'local_emulator':True}
