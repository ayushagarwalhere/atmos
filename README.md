# Atmos

An interactive concept for a North India smoke transport digital twin. It explores how crop-fire clusters in Punjab and Haryana could connect to wind transport, city air readings, scenario estimates and audience-specific impact views.

## Run locally

Requires Node.js 20.19+ or 22.12+.

```sh
npm install
npm run dev
```

Open the address Vite prints (normally http://127.0.0.1:5173).

```sh
npm run build
npm run preview
```

## Current prototype

- Atmos name, sky/dark theme toggle, scroll-based atmospheric intro, responsive navigation and motion preferences.
- A regional map concept with fire clusters, downwind city nodes, transport links, a selected-city summary and interactive wind/fire scenario sliders.
- Illustrative AQI, PM2.5, fire counts, FRP and arrival estimates. These values are UI demo data only. The site does not connect to NASA FIRMS, Open-Meteo, CPCB, OpenAQ, AWS or a trained forecast model.
- The Data & Method section calls out integration gates and limits. Historical city AQI availability must be verified before any machine-learning claim.

## Proposed data and model path

1. Validate station-level historical AQI access for the target cities. Then ingest NASA FIRMS detections (with an API key) and hourly Open-Meteo wind data into SQLite or Postgres.
2. Cluster fire detections, define city/station nodes and estimate transport with wind drift; treat HYSPLIT as a later upgrade.
3. Compare persistence and linear baselines with tabular models using time-based validation. Add prediction intervals and feature explanations only when supported by evaluation.
4. Use an agent framework such as AWS Strands Agents SDK to call the data and model tools. Require tools to return evidence and uncertainty; agents must not invent measurements.
5. Validate arrival estimates against past AQI changes and document misses, satellite detection gaps and other pollution sources.

## Build

```sh
npm run build
```
