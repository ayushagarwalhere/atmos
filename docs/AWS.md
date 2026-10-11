# Atmos on your AWS profile

Environmental Hacks lists Strands Agents SDK in the **Build It** stack. Atmos already uses the actual Strands orchestrator/tool protocol and a five-node Strands graph. Adding Bedrock and cloud data services is optional and does not require replacing the local frontend or its animation.

## Prepared cloud integration

| Component | Purpose | Status |
| --- | --- | --- |
| Strands Agents SDK | Orchestrator, specialist tools, dependency graph and persisted graph execution | Implemented locally |
| Amazon Bedrock | Language-model routing/reasoning through the selected AWS profile | Adapter implemented; account/model access required |
| Amazon S3 | Private evidence JSON artifacts, partitioned by demo/live mode | Adapter and resource template prepared |
| Amazon DynamoDB | Cloud mirror of run ID, mode, city, status and artifact pointer | Adapter and on-demand table prepared |
| Amazon SQS | Optional analysis queue and local worker, with ledger-based duplicate claims | Adapter and queue/DLQ prepared |
| Amazon CloudWatch | Completion and analysis-duration metrics | Adapter and log group prepared |
| IAM EC2 role | Temporary runtime credentials scoped to this stack | Instance profile prepared |
| OpenSearch | Optional local full-text evidence index/search | Adapter prepared; SQLite FTS5 is the default |
| AWS SAM | Separate local Lambda evidence-manifest function | Source/template prepared; SAM runtime needed |

`infra/cloud.yaml` prepares a private S3 bucket, DynamoDB table, SQS analysis queue/dead-letter queue, CloudWatch log group and scoped EC2 application role/profile. It does not create hosting, IAM users/access keys or public buckets. See [the smoke twin guide](SMOKE_TWIN.md) for current runtime statuses and numerical-method limitations.

## Configure authentication

Use an existing AWS SDK profile (including IAM Identity Center/SSO), with a session that can access the intended services. Do not paste keys into chat or frontend code. `AWS_PROFILE` selects the profile; `AWS_REGION` selects the region. If the profile uses SSO, authenticate it through your normal AWS CLI login flow before starting Atmos.

The backend constructs an explicit `boto3.Session` for both Bedrock and data-service clients. The emulator path uses dummy credentials; the AWS path uses the real profile. Credential values are never returned by the health API.

Review `.env.aws.example`, then merge the settings you want into `.env` (preserve your FIRMS/OpenAQ keys):

```dotenv
AWS_PROFILE=your-profile-name
AWS_REGION=your-region
ATMOS_AGENT_PROVIDER=bedrock
BEDROCK_MODEL_ID=your-tool-capable-model-or-inference-profile
ATMOS_AWS_MODE=aws
ATMOS_AWS_ALLOW_WRITES=false
```

The model must support Bedrock Converse tool use and be available to the chosen account/region. The configured model ID is not proof of availability. Mumbai (`ap-south-1`) is the initial data-service region for this India-based project. Verify model availability separately: Nova Lite v1 lists geographic cross-region inference for Mumbai, so discover the account's supported inference profile rather than assuming its direct model ID works there.

Set `ATMOS_EXPECTED_AWS_ACCOUNT` to the intended 12-digit account ID. Every real SDK session checks STS identity before service access. Authentication and model access must succeed before enabling Bedrock.

### Application spending controls

The user's total allowance is **$25**. Paid inference stays blocked until verified current model/region input and output prices are supplied through `ATMOS_BEDROCK_INPUT_USD_PER_MILLION` and `ATMOS_BEDROCK_OUTPUT_USD_PER_MILLION`. Before each SDK stream the app atomically reserves a conservative byte-based input estimate plus the maximum output cost. Its lifetime ledger pauses inference at **$5 in reservations or 100 calls**, whichever occurs first. Failed calls retain their reservation. Each request is limited to 50 KB of conversation/tools and 512 output tokens; automatic SDK retries are disabled. Real data-service operations pause at 1,000 calls, and evidence uploads are limited to 2 MB each. The ledger can be viewed at `/api/aws/budget`.

These controls leave headroom, but **they are not an account-wide $25 hard stop**. Storage, taxes, other applications, cross-region costs and changed pricing are outside this ledger. Preserve the data directory; deleting it resets reservations. Use an AWS Budget alert as an additional measure and check account charges before deployment; AWS documents delayed budget updates. A full five-specialist analysis can invoke multiple model/tool turns.

## Review resources before creating them

The resource file is [infra/cloud.yaml](../infra/cloud.yaml). Choose a globally unique evidence bucket name and a resource prefix. Review a CloudFormation change set in the selected profile/region before execution. Deployment requires AWS permissions and may incur charges; this repository does not deploy automatically.

After creating the reviewed stack, set its output names:

```dotenv
ATMOS_S3_BUCKET=stack-evidence-bucket-output
ATMOS_DYNAMODB_TABLE=stack-run-table-output
ATMOS_SQS_QUEUE=stack-analysis-queue-name-output
```

Use **Check cloud connections** in the AWS services workspace. It performs S3 HeadBucket, DynamoDB DescribeTable and SQS GetQueueUrl calls, plus a CloudWatch metric write when enabled and writes are permitted. It does not provision resources or invoke Bedrock. Restart the backend after enabling the provisioned resources. Completed simulations and analyses publish evidence to S3 and metadata to DynamoDB; a failed cloud write retains the local report and reports the error.

Cloud bootstrap is deliberately rejected by the application: provisioning is managed by the reviewable stack. Runtime permissions should be restricted to this bucket/table/queue and the selected Bedrock model/inference profile. Required operations are S3 ListBucket/PutObject, DynamoDB DescribeTable/PutItem, SQS GetQueueUrl/SendMessage/ReceiveMessage/DeleteMessage and Bedrock InvokeModel/InvokeModelWithResponseStream. Scope inference-profile and destination-model permissions according to your selected model's requirements.

### Optional queued execution

```dotenv
ATMOS_ANALYSIS_QUEUE=sqs
```

Start a local worker using the same profile/configuration:

```powershell
.venv-atmos\Scripts\python.exe -m scripts.aws_local worker
```

The API also wakes a bounded worker after enqueueing an analysis. It consumes one message at a time, atomically claims its SQLite run, executes the Strands graph, then deletes the message. Keep any manual worker pointed at the same `ATMOS_DATA_DIR`. This queue integration still depends on the instance's SQLite ledger. After a backend restart, unfinished runs are marked interrupted; rerun deliberately to generate new evidence. Stored results remain readable.

## Costs and cleanup

Bedrock inference, S3 storage/requests, DynamoDB requests/storage and SQS requests can incur charges. AWS credit eligibility varies by account; do not assume every operation is free. The stack uses on-demand DynamoDB and does not create always-running cloud compute.

S3 evidence expires after 30 days. The bucket is retained when the stack is deleted, so a stack deletion alone does not remove all storage charges. A cleanup requires reviewing the contents, then emptying/deleting the retained bucket yourself. Queue messages expire after one day; the stack supplies a dead-letter queue. Actions/alert delivery are separate: this integration does not automatically contact anyone.

## Optional emulator path

The emulator remains useful for regression checks but is not the recommended cloud authentication path. Moto is a third-party testing emulator, not an AWS product. To run it without Docker:

```powershell
.venv-atmos\Scripts\python.exe -m pip install -r requirements-build-it.txt
.venv-atmos\Scripts\moto_server.exe -H 127.0.0.1 -p 5000
```

Set `ATMOS_AWS_MODE=local`, `ATMOS_AWS_ENDPOINT=http://localhost:5000`, leave cloud resource variables empty, and run `.venv-atmos\Scripts\python.exe -m scripts.aws_local bootstrap`. `compose.build-it.yml` also supplies optional Moto and OpenSearch services; it binds their ports to loopback only. Its OpenSearch security-disabled configuration is for isolated local development, not cloud deployment.

For OpenSearch set `ATMOS_OPENSEARCH_URL=http://localhost:9200` and index the library from the workspace. Retrieval always filters demo/live and city; unavailable OpenSearch falls back to SQLite with an explicit error label.

For the optional SAM manifest function, install AWS SAM CLI and a supported container runtime, then use `sam build -t infra/template.yaml` and `sam local invoke EvidenceManifest --event your-evidence-pointer.json`. The event is `{"key":"demo/your-artifact-id.json"}`. The Lambda reads the local S3 emulator and returns a SHA-256 manifest; it does not forecast air quality.

## Primary documentation

- [Hackathon Build It requirements](https://www.wemakedevs.org/aws/env)
- [AWS profile configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- [Bedrock pricing](https://aws.amazon.com/bedrock/pricing/)
- [Nova Lite regional availability](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-lite.html)
- [AWS Budgets update delays](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
- [Strands graph API](https://strandsagents.com/docs/api/python/strands.multiagent.graph/)
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/using-sam-cli.html)
