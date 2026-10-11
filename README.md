# Atmos — smoke transport twin

A local research prototype for Punjab/Haryana fire detections and downwind Delhi, Chandigarh, Ludhiana and Lucknow. The original cloud descent, animated window, Atmos branding and sky/dark themes are preserved. A new flowing WebGL interlude introduces the smoke twin.

## Run the full application

Requires Node.js 20.19+ or 22.12+ and Python 3.11+ (3.12 recommended).

```powershell
npm install
py -3.12 -m venv .venv-atmos
.venv-atmos\Scripts\python.exe -m pip install -r requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
npm run dev:full
```

Open **http://127.0.0.1:5173**. Vite proxies `/api` to FastAPI at port 8000. This checkout has a working `.venv311`; the launcher skips the incompatible `.venv-atmos` environment. `npm run dev` starts only the frontend; `npm run api` starts only the backend. For a built application, run `npm run build`, then `npm run api` and open http://127.0.0.1:8000. API documentation: http://127.0.0.1:8000/docs.

Use `py -3.11` if Python 3.12 is unavailable. Avoid recreating an existing environment with a different Python version: installed native packages belong to its original interpreter. The launcher checks FastAPI imports and selects the first working environment from `.venv-atmos`, `.venv`, and `.venv311`. `ATMOS_PYTHON` can select an explicit interpreter. If a recreated environment reports a Pydantic native import error, create a fresh environment in a new directory, install `requirements.txt` there, and set `ATMOS_PYTHON` to its Python executable.

Demo mode uses reproducible synthetic records, clearly labeled throughout. Live mode reads only real provider/imported records and reports missing inputs. SQLite and trained artifacts are in ignored `data/`; credentials stay in the backend `.env`.

Run `npm run demo:prepare` once to prepare synthetic models for 6, 12 and 24 hours before a demo. CSV uploads or pasted CSV contents are stored in Live data and automatically select that mode. Weather CSVs can include rain, cloud cover, humidity and temperature; blanks remain missing. All forecast, scenario, impact and specialist evidence uses the selected mode's stored inputs.

## Implemented phases

The expanded analysis workspace runs a real five-specialist Strands graph with persistent runs, streamed events, saved evidence/search, an audit ledger and tracked action plans. See [architecture](docs/ARCHITECTURE.md) and the [AWS profile setup guide](docs/AWS.md). Your AWS profile can power Bedrock inference and S3/DynamoDB/SQS; the reviewed resource template is [infra/cloud.yaml](infra/cloud.yaml). Cloud writes default off and resources are not automatically created.

| Phase | Implementation |
| --- | --- |
| Data | NASA FIRMS VIIRS, Open-Meteo forecast/archive wind, rain, clouds, humidity and temperature, OpenAQ v3 hourly station PM2.5, filtered official PIB RSS; SQLite tables, provenance, status and scheduled refresh. |
| Nodes | DBSCAN fire clusters with center, timestamp, count and total FRP; four city nodes and nearest station metadata. |
| Edges | Hourly wind drift, distance, bearing, arrival, spread and transport score; moving map particles and selectable nodes. |
| Forecast | Persistence, standardized Ridge, XGBoost and LightGBM; chronological selection/calibration/test splits with horizon purging; MAE/RMSE comparisons, split conformal intervals and tree SHAP/linear contributions. |
| Agents | AWS Strands orchestrator and intelligence, forecast, scenario, impact and strategy specialists calling evidence tools. The default deterministic local router needs no model credentials; optional Ollama/Bedrock enables language models. |
| Twin | Pan/zoom graph, source details, city forecasts and explanations, last-48-hour replay, future horizon, weather/fire/burning scenarios, baseline comparisons and grounded chat. |
| Alerts | Persisted severity, transport score and interval coverage thresholds, cooldown and suppression reasons; in-app events and optional email/Telegram delivery. |
| Validation | Arrival backtest with hits, misses and false negatives, exportable forecast comparison and evidence, source limitations and government-tool comparison. |

### Use real data

Set `FIRMS_MAP_KEY` and `OPENAQ_API_KEY` in `.env`, restart, choose **Live** and **Refresh providers** in Data. Open-Meteo needs no key. Provider failures retain existing records and are shown in the UI. OpenAQ coverage depends on city and dates; real historical availability cannot be confirmed without a key and usable readings.

The Data panel accepts fire, wind, station PM2.5, facility and news CSVs and downloads format templates. Timestamps require an explicit UTC offset. NASA archived fire CSVs support historical training; the history loader fetches Open-Meteo archives and OpenAQ readings for past ranges up to 90 days. There is no unverified CPCB scraper.

Training requires aligned fire, wind and PM2.5 history, at least 240 usable examples and 14 days of issue times. In practice, several weeks are preferable. Use **Train real history** for live records, or the separately labeled **Run demo pipeline** to exercise the four-model workflow on synthetic records. Model selection retains persistence unless a candidate improves selection MAE by at least 5%. Held-out performance and interval coverage are reported separately. Insufficient history produces a readable error rather than invented results.

### Weather and burning scenarios

Open **Scenario** to change wind direction/speed, hourly rain, cloud cover and fire activity. Select an assumed burning source; the advanced controls include a smoke-emission proxy multiplier, humidity, mixing height and temperature. **Calm + burning**, **Rainy**, and **Clear + windy** are explicit what-if presets. Reset restores the original feed inputs. A selected scenario stays applied when opening Forecast, Impact and the specialist workflow; exported evidence retains all assumptions and the unchanged baseline.

The forecast learns weather associations from training history. Rain is the previous-hour rainfall in millimetres, cloud cover is a percentage, and mixing height is in metres. Controls replace issue-hour features; they do not impose a full future weather schedule. Changing the smoke proxy scales the upwind FRP feature per detection without changing detected fire counts. Burning source selection adds context but does not claim fuel-specific emissions. Zero fire activity or a zero smoke proxy produces no smoke-arrival paths, while other pollution sources can remain.

Use **Train demo model** or **Run demo pipeline** to explore numerical differences on deliberately synthetic weather/pollution relationships. Demo training evaluates the software only. Live scenarios need retraining with matched real weather and PM2.5 history. Older model artifacts are detected and safely fall back to persistence until retrained. A persistence forecast keeps the latest station reading; it cannot quantify a weather response. Scenario uncertainty is not calibrated, and clouds have no universal positive or negative PM2.5 effect.

Variable definitions: [Open-Meteo](https://open-meteo.com/en/docs). Physical context: [EPA smoke transport and deposition](https://www.epa.gov/sciencematters/tracking-smoke-models-protect-public-health), [EPA smoke composition](https://www.epa.gov/wildfire-smoke-course/wildfire-smoke-complex-mixture). The drift paths remain independent of wet deposition and cloud chemistry.

### Agent execution

`ATMOS_AGENT_PROVIDER=local_rules` uses an offline deterministic model adapter inside actual Strands agent/tool loops. It is explicitly not an LLM. Forecast facts and numeric answers are assembled from tool evidence; generated model prose cannot override those values.

For local language models, install/run Ollama separately, pull the model you choose, set `ATMOS_AGENT_PROVIDER=ollama`, `OLLAMA_HOST` and `OLLAMA_MODEL`. For AWS, choose `bedrock`, configure normal AWS credentials and a region/model you have access to. These optional runtimes are not bundled or automatically provisioned. Missing runtime configuration returns an explicit fallback notice and grounded tool evidence.

### Alerts and impact

Demo and scenario results cannot send alerts. Live sending additionally requires a fresh prediction, a validated real model that beats persistence, sufficient held-out interval coverage, transport/severity thresholds and cooldown. External delivery defaults off; enable it explicitly with `ALERT_SEND_ENABLED=true` and SMTP or Telegram configuration. **Check eligibility** evaluates rules without sending external messages.

Load school/hospital locations from OpenStreetMap in the Impact panel or import your own facility/district CSV. Counts mean inventory points intersecting an estimated corridor, not verified exposure. Population remains unknown unless supplied; OSM inventories are incomplete.

## Scientific limits

- Hotspots are satellite detections, not verified stubble fires. The regional bounding box includes neighboring areas; satellite overpasses miss some fires.
- Ten-meter wind drift is a simplified corridor estimate, not NOAA HYSPLIT or a calibrated dispersion model. Its transport score is not a probability.
- The target is hourly PM2.5 in µg/m³. The separately displayed 24-hour PM2.5 sub-index requires enough readings and is not overall Indian AQI.
- Pollution has multiple sources. Correlation, SHAP contribution and arrival coincidence do not establish smoke-source causation.
- Weather archives and replay/backtests are hindcasts, not proof of operational forecast performance. Scenario intervals are not calibrated for the intervention.
- Synthetic validation checks the software/model pipeline. Real forecasting quality remains unvalidated until sufficient real history is imported and evaluated.
- HYSPLIT and LSTM were optional stretch goals and are not included.

## Checks

```powershell
npm run verify
```

Runs backend and optional AWS integration checks and production frontend build. Checks cover clustering, meteorological direction/calm behavior, replay, source partitioning, scenario drift, actual model training/time splits, Strands execution, alert suppression and arrival backtesting. `npm run test:backend` runs only backend checks. The build reports a large bundle warning because it contains Three.js and the original 3D opening.

## Sources and design references

- [NASA FIRMS area API](https://firms.modaps.eosdis.nasa.gov/api/area/), [Open-Meteo](https://open-meteo.com/en/docs), [OpenAQ](https://docs.openaq.org/), [AWS Strands](https://strandsagents.com/docs/).
- [IITM Decision Support System](https://ews.tropmet.res.in/dss/index.php) already provides regional air-quality/source and intervention forecasts. Atmos emphasizes an inspectable interactive graph, local tool evidence, scenario controls and explicit software validation; it does not claim superior atmospheric forecasting.
- [Government stubble-monitoring context](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2223752).
- Animation/composition references: [Mohit Virli](https://github.com/mohitvirli/mohitvirli.github.io), [React Three Fiber](https://github.com/pmndrs/react-three-fiber), [Atmos Gallery](https://atmos.gallery/). The new interlude uses an original procedural shader and existing typography; no gallery media was copied.
