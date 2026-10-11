# Regional smoke twin

## Interactive demonstration

Open the regional smoke twin and choose **Run demo**. Atmos runs a 50% burning reduction against a baseline with the same issue time, city and horizon. The Simulate workspace follows a template -> configuration -> run -> comparison workflow. Eight templates cover fire surges, burning reduction/pause, rain, ventilation, wind direction, stagnation and shallow night-time mixing.

All ten assumptions are editable. Completed runs are stored on the server for the browser's session; saved configurations remain in browser storage. Compare up to three runs with matching city, mode, issue time and horizon, apply a run to the map, or export its complete JSON report. A historical report keeps its original time rather than silently using today's conditions.

Explore includes regional outlines, fire/path/city/exposure layer switches, pan/zoom and a -48h to +24h timeline with pause, step and return-to-now controls. Future positions represent forecast horizons from the issue time. Paths and exposure screening are limited to the selected outlook. Maximize uses browser fullscreen when available with a CSS fallback and Escape/focus handling.

### Run the five Strands specialists

1. Choose **Run demo**. This runs the 50% fire-proxy reduction and shows a baseline/what-if comparison.
2. Select **Run five-agent analysis** below that report. Atmos carries over the same city, issue time, horizon and scenario settings.
3. Watch each specialist call its evidence tool in order: **Intelligence** gathers fires/stations/provider freshness; **Forecast** reads the smoke path and city forecast; **Scenario** compares the baseline with your controls; **Impact** screens the supplied schools/hospitals; **Strategy** prepares audience-specific next steps.
4. Read the five findings, open any card's evidence, inspect the event stream, update the proposed action plan, or export the saved analysis JSON. Select **Analysis** directly to run the five-agent workflow without first running a what-if.

The graph and tools use the Strands Agents SDK. With `ATMOS_AGENT_PROVIDER=local_rules` (the public demo default), the SDK still executes the tool loops and graph, while a deterministic offline router selects tool calls; it does not generate free-form model reasoning and incurs no model inference charge. Bedrock and Ollama are optional providers. Every figure and action stays grounded in server-side evidence tools; generated text cannot override tool results. Demo data and scenario responses are synthetic. Data & imports contains model evaluations, CSV formats/uploads and alert configuration. CSVs enter live storage with provenance; demo and live records remain separate. Visitors share imported data in this public demonstration; session-scoped report IDs are not a full user-account system.

## Numerical method

Demo inputs and weather/fire response coefficients are explicitly synthetic. The response recipe combines changes in the upwind FRP proxy, wind speed, rain, cloud, humidity, temperature and mixing height. Direction also changes transport and the upwind proxy. The recipe has no calibrated confidence interval or causal interpretation. Burning-source labels do not supply fuel-specific emission factors.

For live city projections, Atmos uses the latest station PM2.5, recent history, fire/transport and available weather features with a locally trained 6/12/24-hour model. The live validation screen separates chronological train, selection, calibration and test periods. A what-if re-runs the trained model with the selected controls; its interval is withheld because intervention coverage is not calibrated. If there is no suitable trained model, the report says PM2.5 is held at the latest station reading while transport and arrival still respond. The UI identifies which basis produced each result. Live model training requires at least 14 days of aligned station, wind and fire history; imported CSV data can supply those inputs. Open-Meteo archive weather is retrospective hindcast, not historical forecast-vintage data, and fire detections do not establish source attribution.

Live mode uses imported/provider observations and the existing forecast model. Persistence can carry recent station readings forward; its PM2.5 does not change numerically with weather controls until a suitable model is trained. Missing/stale data remain unavailable. Facilities intersecting a widening wind-drift corridor indicate potential exposure, not measured doses. Synthetic and scenario outputs cannot send external alerts.

## AWS integrations

| Component | Purpose | Activation |
| --- | --- | --- |
| EC2 | Docker application hosting and analysis worker | Current site active; migration to owner's account pending account activation |
| EBS | SQLite, models and saved local reports | Active on current hosting instance |
| VPC | Instance network and web/SSH access rules | Active on current hosting instance |
| S3 | Private evidence and simulation report JSON | Stack and instance role required |
| DynamoDB | Run metadata/report pointers with 30-day TTL | Stack and instance role required |
| SQS | Bounded queue worker and dead-letter queue | Set `ATMOS_ANALYSIS_QUEUE=sqs` after provisioning |
| CloudWatch | Completion/duration metrics; prepared log group | Set `ATMOS_CLOUDWATCH_ENABLED=true` after provisioning |
| CloudFormation | Reproducible data/role infrastructure | `infra/cloud.yaml` |
| IAM | EC2 temporary application credentials | Role and instance profile in the stack |
| Strands Agents SDK | Five-specialist orchestration | Integrated open source SDK, not a hosted AWS service |
| Bedrock | Optional paid model inference | Disabled; local rule router currently used |

The AWS services workspace shows runtime status rather than counting templates as deployed services. Connection checks verify S3, DynamoDB and SQS access and publish a CloudWatch check metric when enabled. S3/DynamoDB publication failures retain the local simulation report. SQS wakes a bounded worker on enqueue rather than polling continuously. An instance restart interrupts incomplete local analyses; deliberately rerun them.

Runtime AWS user credentials are never copied to EC2. Attach the stack's EC2 instance profile in the **same account as the instance**. Docker bridge networking needs IMDSv2 enabled with response hop limit 2. Do not attach a role to a friend's instance using credentials for another account.

Storage, requests, metrics, logs and hosting can incur charges. Report/object retention and application call limits reduce usage; they are not an account-wide billing cap. Retained S3/DynamoDB resources survive stack deletion. Review [AWS pricing](https://aws.amazon.com/pricing/) and account charges.

## Design references

- [Prism.ai](https://github.com/harshbpathak/prism.ai), revision `0a6cfbfe7f364894cdb3952f5377eeb17509ae37`: template/configure/run/result workflow inspiration. Atmos implements its own React controls and smoke-specific backend; Prism's Next/auth stack is not imported.
- [Windy Compare Forecast](https://community.windy.com/topic/26304/understanding-the-compare-forecast-feature-in-windy-com): side-by-side comparisons with aligned context.
- [Ventusky help](https://www.ventusky.com/help): timeline stepping, playback and layer controls.
- [Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/): public-domain approximate regional boundaries, extracted from `natural-earth-vector` 10m admin-1 data. These outlines are a visualization aid, not an authoritative boundary map.

Infrastructure preparation uses the installed AWS storage, IAM and CloudFormation skills. IAM Policy Autopilot was run against the AWS adapter. Its broad development/bootstrap baseline was not uploaded; the application's existing scoped runtime role excludes emulator resource-creation permissions.

```powershell
uvx iam-policy-autopilot@latest generate-policies C:\Users\agarw\Desktop\air-envHack\backend\aws_services.py --region eu-north-1 --account 400428376487 --service-hints s3 dynamodb sqs cloudwatch sts --pretty
```
