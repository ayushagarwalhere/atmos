"""Provision Atmos data services using CLI login; never export user credentials."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--region', default='eu-north-1')
    parser.add_argument('--expected-account', required=True)
    parser.add_argument('--stack', default='atmos-data')
    parser.add_argument('--instance-id', help='Optional existing instance in the same account; does not create hosting')
    parser.add_argument('--create-host', action='store_true', help='Create an owned EC2 host after the data stack')
    parser.add_argument('--key-name', help='Existing EC2 key pair in the selected account and region')
    parser.add_argument('--ssh-cidr', help='Operator public IPv4 /32 for the new host')
    parser.add_argument('--instance-type', default='t3.small', choices=['t3.small','t3.medium'])
    args = parser.parse_args()
    if args.create_host and (args.instance_id or not args.key_name or not args.ssh_cidr):
        parser.error('--create-host requires --key-name and --ssh-cidr, without --instance-id')
    if args.ssh_cidr:
        import ipaddress
        network = ipaddress.ip_network(args.ssh_cidr, strict=True)
        if network.version != 4 or network.prefixlen != 32:
            parser.error('SSH access must be restricted to one IPv4 /32')
    executable = shutil.which('aws')
    if not executable and os.name == 'nt':
        executable = str(Path(os.environ['LOCALAPPDATA']) / 'Programs/Amazon/AWSCLIV2/aws.exe')
    def call(*parts, raw=False):
        result = subprocess.run([executable, *parts, '--profile', args.profile, '--region', args.region, '--no-cli-pager'], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr.strip())
        return result.stdout if raw else json.loads(result.stdout or '{}')
    identity = call('sts', 'get-caller-identity')
    if identity['Account'] != args.expected_account:
        raise ValueError('Signed-in account does not match the intended deployment account.')
    if args.instance_id:
        instance = call('ec2', 'describe-instances', '--instance-ids', args.instance_id)['Reservations'][0]['Instances'][0]
        if instance.get('IamInstanceProfile'):
            raise ValueError('Instance already has an IAM profile. Review it before replacing the role.')
    bucket = f'{args.stack}-evidence-{identity["Account"]}-{args.region}'
    print(f'Provisioning {args.stack} in the intended account and {args.region}.', flush=True)
    call('cloudformation', 'deploy', '--stack-name', args.stack,
         '--template-file', str(ROOT / 'infra/cloud.yaml'), '--capabilities', 'CAPABILITY_IAM',
         '--parameter-overrides', f'EvidenceBucketName={bucket}', f'ResourcePrefix={args.stack}',
         '--no-fail-on-empty-changeset', raw=True)
    stack = call('cloudformation', 'describe-stacks', '--stack-name', args.stack)['Stacks'][0]
    outputs = {item['OutputKey']: item['OutputValue'] for item in stack['Outputs']}
    if args.instance_id:
        call('ec2', 'modify-instance-metadata-options', '--instance-id', args.instance_id,
             '--http-tokens', 'required', '--http-put-response-hop-limit', '2')
        call('ec2', 'associate-iam-instance-profile', '--instance-id', args.instance_id,
             '--iam-instance-profile', f'Name={outputs["ApplicationProfileName"]}')
    config = {
        'AWS_REGION': args.region, 'ATMOS_EXPECTED_AWS_ACCOUNT': identity['Account'],
        'ATMOS_AWS_MODE': 'aws', 'ATMOS_AWS_ALLOW_WRITES': 'true', 'ATMOS_AGENT_PROVIDER': 'local_rules',
        'ATMOS_S3_BUCKET': outputs['EvidenceBucket'], 'ATMOS_DYNAMODB_TABLE': outputs['RunTable'],
        'ATMOS_SQS_QUEUE': outputs['AnalysisQueueName'], 'ATMOS_ANALYSIS_QUEUE': 'sqs',
        'ATMOS_CLOUDWATCH_ENABLED': 'true', 'ATMOS_CLOUDFORMATION_STACK': args.stack,
        'ATMOS_CLOUDWATCH_LOG_GROUP': outputs['ApplicationLogGroup'],
    }
    # Only public resource identifiers: no access keys, tokens or login cache.
    config_path = ROOT / '.cache/atmos-cloud.env'
    config_path.parent.mkdir(exist_ok=True)
    config_path.write_text(''.join(f'{key}={value}\n' for key, value in config.items()))
    print(f'Resources ready. Runtime resource configuration: {config_path}', flush=True)
    if args.create_host:
        try:
            call('cloudformation', 'describe-stacks', '--stack-name', args.stack+'-hosting')
        except RuntimeError as error:
            if 'does not exist' not in str(error):
                raise
        else:
            raise ValueError('Hosting stack already exists. This creation command will not replace a running instance.')
        print('Creating owned hosting. EC2, disk and public IPv4 incur hosting charges.', flush=True)
        call('cloudformation', 'deploy', '--stack-name', args.stack+'-hosting',
             '--template-file', str(ROOT / 'infra/hosting.yaml'), '--parameter-overrides',
             f'ApplicationProfileName={outputs["ApplicationProfileName"]}', f'KeyName={args.key_name}',
             f'SshCidr={args.ssh_cidr}', f'InstanceType={args.instance_type}', '--no-fail-on-empty-changeset', raw=True)
        host_stack = call('cloudformation', 'describe-stacks', '--stack-name', args.stack+'-hosting')['Stacks'][0]
        host_outputs = {item['OutputKey']: item['OutputValue'] for item in host_stack['Outputs']}
        (ROOT / '.cache/atmos-hosting.json').write_text(json.dumps(host_outputs, indent=2))
        print(f'Host created: {host_outputs["InstanceId"]}, IP {host_outputs["PublicIp"]}. Configure the app and HTTPS before cutover.')
    else:
        print('Attach the application profile to an owned EC2 instance before activating this configuration there.')

if __name__ == '__main__':
    main()
