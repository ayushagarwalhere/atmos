# Move Atmos to an owned AWS account

The current HTTPS site is on a friend's EC2 instance. The signed-in `atmos` profile belongs to the project owner's account. EC2/CloudFormation currently return `OptInRequired` in that account, so no new AWS resources have been created.

## Required account step

Complete any pending activation, payment/customer verification or subscription prompts in the AWS account's Billing/Account console. The Builder ID profile editor does not display that account status. Then confirm EC2 calls work with the signed-in profile and explicit `eu-north-1` region. Never send access keys or login-cache files to GitHub or EC2.

## Prepared infrastructure

- `infra/cloud.yaml`: private report bucket, run metadata table, queue/DLQ, log group and application role/profile.
- `infra/hosting.yaml`: dedicated network and small Ubuntu EC2 host, encrypted 24 GB gp3 volume, stable public IP, IMDSv2, public 80/443 and operator-only SSH. The app's port 8000 remains private. CPU credits use standard mode. User data installs prerequisites and clones the public repository; app activation and HTTPS setup follow separately.
- `scripts/provision-aws.py`: uses the installed AWS CLI and its temporary login; verifies the intended account; saves resource identifiers in ignored `.cache` files. It refuses to replace an existing hosting stack or overwrite an instance's existing role.

Provisioning EC2, its disk/public IP and data/monitoring services incurs charges. Review current regional pricing and the project allowance before creating a host. Existing and new hosts overlap during migration. Retained EBS, S3 and DynamoDB data require separate cleanup after stack deletion.

For data services only:

```powershell
.\.venv311\Scripts\python.exe scripts/provision-aws.py --profile atmos --region eu-north-1 --expected-account YOUR_ACCOUNT_ID
```

For a new host, first import the public half of a local SSH key as an EC2 key pair in the intended account and region. Private key material stays on the operator's computer. Then pass its EC2 key-pair name and the operator's actual public IPv4 `/32`:

```powershell
.\.venv311\Scripts\python.exe scripts/provision-aws.py --profile atmos --region eu-north-1 --expected-account YOUR_ACCOUNT_ID --create-host --key-name YOUR_KEY_PAIR --ssh-cidr YOUR_PUBLIC_IP/32
```

## Cutover work

1. Wait for cloud-init prerequisites to finish and obtain the new instance's verified SSH host key through the AWS console/API.
2. Snapshot the current SQLite database consistently and transfer the persistent data/models/Strands sessions directly to the new host. Preserve the application budget ledger. Keep the backup out of GitHub.
3. Merge the generated public resource configuration into the new server's root-owned `atmos.env`; retain `ATMOS_AGENT_PROVIDER=local_rules` and external alerts disabled. The attached EC2 role supplies temporary AWS credentials. Do not copy `AWS_PROFILE` or the Windows login cache.
4. Deploy the published revision with `scripts/deploy-ec2.sh`, configure Nginx for the new IP and a trusted Let's Encrypt short-lived IP certificate, and install its renewal timer. Keep HTTP ACME validation accessible. Replace the old hardcoded IP in the Nginx configuration.
5. Configure CI access for the new host before changing GitHub deployment secrets. The new security group restricts SSH to the operator; GitHub-hosted runners need an explicitly configured deployment route (for example an AWS OIDC/Systems Manager route). Do not widen SSH to the internet to make CI work.
6. Confirm the public site, runtime role and report/queue/metric delivery. Cut over the public link and CI destination together. Do not terminate the friend's instance or delete its data without explicit owner authorization.

Migration is pending the account activation step. The current HTTPS link continues serving the completed smoke twin update meanwhile.
