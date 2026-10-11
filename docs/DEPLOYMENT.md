# Deploy Atmos on AWS

The current application is a single FastAPI service that serves both the built React UI and `/api`. Its SQLite database, model files, budgets and Strands sessions require a persistent data directory. The existing `infra/cloud.yaml` provisions optional evidence services; it does not host the application.

## Recommended first deployment: one EC2 instance

Use one Linux EC2 instance with an EBS volume. Choose enough memory for the numerical Python packages; model training needs more memory than serving saved models. Review the selected instance, storage and public IPv4 pricing against your $25 allowance. Avoid a load balancer, NAT gateway and managed OpenSearch cluster for a small demonstration.

1. Create a Linux EC2 instance and allow SSH only from your IP. Install Docker using its official instructions for that operating system. Copy the repository to the instance, excluding local credentials and virtual environments.
2. Build the supplied container in the project directory:

   ```sh
   docker build -t atmos:latest .
   docker volume create atmos-data
   ```

3. Create a server-only `atmos.env` file from `.env.example`, adding your FIRMS/OpenAQ keys if using live providers. The container's data path is `/app/data`. Start with `ATMOS_AGENT_PROVIDER=local_rules`, `ATMOS_AWS_MODE=disabled` and `ATMOS_AWS_ALLOW_WRITES=false`. Do not copy your Windows `AWS_PROFILE` into a server that has no such profile.
4. Prepare the volume permissions and start the service:

   ```sh
   docker run --rm --user 0 -v atmos-data:/app/data atmos:latest chown -R 10001:10001 /app/data
   docker run -d --name atmos --restart unless-stopped --env-file atmos.env \
     -p 127.0.0.1:8000:8000 -v atmos-data:/app/data atmos:latest
   docker exec atmos python -m scripts.prepare_demo
   curl http://127.0.0.1:8000/api/health
   ```

5. For a private demo, keep port 8000 closed in the security group. From your computer, use an SSH tunnel:

   ```sh
   ssh -i your-key.pem -L 8000:127.0.0.1:8000 ubuntu@YOUR_EC2_HOST
   ```

   Open `http://127.0.0.1:8000` locally. Upload your CSVs through the UI. The app stores and processes them on the EC2 volume.

For a public demo URL, point your domain at the instance and put an HTTPS reverse proxy in front of the loopback service. Configure `ATMOS_ALLOWED_HOSTS=atmos.example.com` before restarting the container. The app currently has no multi-user account system; visitors share the demo's data and actions. Allow public ports 80/443, and keep 8000 private. Use one worker with the current SQLite design. Backup the EBS data and preserve the budget ledger.

## Active EC2 deployment and CI/CD

The public demonstration is hosted at **https://13.49.222.44** on Ubuntu EC2. Nginx redirects HTTP traffic, including the EC2 public DNS hostname, to this HTTPS address and forwards requests to the Docker service on `127.0.0.1:8000`. The site is publicly accessible without a login. It uses a trusted Let's Encrypt IP certificate; no custom domain is required.

The GitHub Actions workflow in `.github/workflows/ec2.yml` builds the production image, runs backend tests, frontend unit tests and desktop/mobile browser checks, and deploys successful `main` pushes. The browser checks use a public HTTP origin to catch APIs that only work on HTTPS or localhost. Pull requests run CI only. `workflow_dispatch` also allows a manual build and deployment of `main`.

Configure these repository Actions secrets, then set the repository Actions variable `EC2_DEPLOY_ENABLED` to `true` to enable deployment. Until that variable is set, the workflow runs CI and skips deployment.

| Secret | Value |
| --- | --- |
| `EC2_HOST` | `13.49.222.44` |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | A dedicated deployment key restricted to `/usr/local/bin/atmos-ci-deploy`; the original instance PEM stays local |
| `EC2_KNOWN_HOSTS` | Verified SSH host-key line for the instance |

Deployment checks out the tested commit into `/home/ubuntu/atmos/repo`. `scripts/deploy-ec2.sh` builds it, checks startup with disposable storage, and replaces the live container only after that check passes. A failed live health check restores the previous container. The persistent `atmos-data` Docker volume and server-only `/home/ubuntu/atmos/atmos.env` are reused. The deployed Git SHA is written to `/home/ubuntu/atmos/deployed-revision` and is also stored in the image label.

The instance must accept SSH from the deployment runner and have Docker, Git, Nginx and passwordless sudo for the deployment user. A root-owned copy of `scripts/ci-ssh-entrypoint.sh` is installed as `/usr/local/bin/atmos-ci-deploy`. Its dedicated public key entry uses `restrict,command="/usr/local/bin/atmos-ci-deploy"` in `authorized_keys`, preventing a normal shell and port forwarding. The entrypoint only accepts a Git SHA reachable from this repository's `main` branch. The workflow pins the verified host key and does not change firewall rules, public access settings, or application provider credentials.

Nginx's current configuration is in `infra/nginx-atmos.conf`. Certbot 5.4+ is required for IP webroot validation; the instance uses `/opt/atmos-certbot/bin/certbot`. The certificate is named `atmos-ip` and uses the `shortlived` profile. `certbot.timer` runs renewal with that version and reloads Nginx after successful renewal. Keep `/.well-known/acme-challenge/` publicly accessible over port 80 and keep ports 80/443 open. IP certificates last about six days, so automatic renewal is required.

## Enable the optional AWS services

| Component | Role | Current dependency |
| --- | --- | --- |
| AWS Strands SDK | Agent/tool execution and the five-specialist graph | Runs locally inside the Python app |
| Amazon Bedrock | Optional language-model inference | Model access, region, pricing and budget configuration |
| Amazon S3 | Private evidence JSON artifacts | Bucket + scoped write permissions |
| Amazon DynamoDB | Mirror of run status and evidence pointer | Table + scoped permissions; does not replace SQLite |
| Amazon SQS | Optional queued analysis delivery | Queue + a worker sharing the SQLite data directory |
| CloudFormation | Provision S3/DynamoDB/SQS/DLQ resources | Reviewed `infra/cloud.yaml` change set |
| EC2 and EBS | Host the app and persist local state | Added by the deployment above |
| OpenSearch and SAM/Lambda | Optional evidence-search / manifest integrations | Separate setup; not needed for the main app |

Attach a scoped IAM role to EC2 instead of placing long-lived AWS keys in the image. Set `AWS_REGION`, `ATMOS_EXPECTED_AWS_ACCOUNT` and the resource names in `atmos.env`. Review/create the `infra/cloud.yaml` stack, then use **Check AWS connection**. Enable writes only after the resource and account checks succeed. Bedrock additionally requires the documented model pricing settings and account/region model access; its application ledger is not an account-wide spending cap. Keep SQS disabled unless you run its worker with the same persisted data volume.

See [AWS integration and budget controls](AWS.md) for the exact environment variables and service permissions.

## Other hosting options

S3 hosting can serve static files, but cannot run this Python backend. Splitting the frontend into S3/CloudFront requires a separate API deployment and origin/authentication configuration. ECS/Fargate can run the supplied image, but the current SQLite and single-worker state must be addressed before running multiple replicas. The one-instance EC2 deployment is the smaller first step for this repository.

Official references: [EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html), [ECS/Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html), [S3 static hosting](https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html).
