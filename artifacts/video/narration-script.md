## Smoke travels. Know what arrives.

Smoke from crop burning and other fires can travel far beyond its source. For cities in North India, changing wind and weather make it difficult to understand where smoke might go, when it might arrive, and which places may need closer attention. Atmos connects fire detections, weather and city air readings in one inspectable research prototype.

## Follow the smoke path

The interactive map groups satellite fire detections into clusters, shows their fire radiative power, and traces simplified hourly wind paths toward four cities. Select a city or source, zoom the map, and replay stored history. Arrival times are estimates. The transport score describes alignment and data coverage, rather than the probability that smoke will arrive.

## Understand the city outlook

Each city has a latest particulate reading, a history chart and a forecast horizon. The application compares persistence, Ridge regression, XGBoost and LightGBM using separate chronological periods for training, model selection, calibration and testing. It shows uncertainty and feature explanations. The displayed particulate sub index is separate from the overall official air quality index.

## Explore weather and burning

In the scenario panel, change wind direction and speed, rainfall, cloud cover and fire activity. Additional controls cover humidity, temperature, mixing height and a smoke emission proxy. Compare the result with the unchanged baseline. Rain can remove airborne particles, while clouds affect sunlight and mixing. Numerical responses are learned associations, and their intervention uncertainty is not calibrated.

## Use your own data

Atmos accepts your own fire, weather, station particulate, facility and news data. Download the CSV format, upload a file or paste its contents, and provide the source. A successful import selects live data automatically. Your uploaded readings and weather values then feed forecasts, scenarios and specialist evidence. Missing inputs stay missing, and invalid files show a readable error.

## Screen places that may need attention

The impact view screens school, hospital and district locations against the estimated smoke corridor. You can import an inventory or load available OpenStreetMap locations. Counts describe potential corridor intersections, not measured exposure or harm. Population stays unknown unless you supply a sourced value. This helps users decide which locations need verification.

## Five specialists, one evidence workflow

Run a complete city analysis to execute five specialists through the AWS Strands graph. Intelligence checks the inputs, Forecast reads the outlook, Scenario compares assumptions, Impact screens places, and Strategy proposes verification steps. The interface shows tool events and saves the result. Every returned number comes from computed evidence. The default provider uses deterministic local rules.

## Keep the evidence and follow through

Analyses survive a backend restart. Search the evidence library, export a result or audit trail, and track proposed actions through accepted, in progress or done. Alert rules check freshness, model validation, uncertainty coverage and cooldowns. Demo and scenario outputs cannot send external alerts. Sending email or Telegram requires separate configuration.

## Useful, inspectable and ready to extend

For deployment, a single EC2 instance can serve the built interface and Python API with persistent storage. Optional integrations use Bedrock for language model inference, S3 for evidence, DynamoDB for run metadata, and SQS for queued analysis. Atmos can support student demonstrations and preliminary planning discussions. This walkthrough uses synthetic data. Real forecasting quality still requires real history and validation, and the app does not establish the pollution caused by a particular fire.