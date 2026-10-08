# AlgaeAir

An atmospheric React frontend for a cloud-connected microalgae bioreactor concept, built for Environmental Hacks 2026 / Track 01: Air.

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

## What is included

- Your palette: cerulean #8EB1D1, baby blue #A7C7E7, midnight blue #1C2B48, platinum #E8ECEF, light blue grey #C4D8E5.
- A procedural Three.js bioreactor with floating motion, illuminated rings and animated bubbles, rendered through React Three Fiber. No additional pod GLB is needed.
- A continuous fullscreen opening using the same seeded Drei cloud banks and downward camera choreography as the Mohit Virli reference: sky title → cloud descent → handle turn → sash opening → flight through the window → camera emergence → AlgaeAir pod reveal. GSAP reveals and Lenis keep the rest of the page smooth.
- A branded looping SVG intro with a shrink-and-wipe transition. This is an original interpretation of the Buttermax loader, not a copy of their Lottie asset.
- Self-hosted DM Sans and Instrument Serif fonts. No font upload is needed.
- The supplied window.glb is animated in the opening and appears in the idea section. Cloud texture and Draco decoding assets are served locally. The Dali and Wanderer models remain untouched in models/ because they do not represent the product.
- A local console with three sample cities, India AQI scenarios, an adjustable AQI slider, a staged event sequence, baseline recovery, an activity log and JSON manifest export.
- Mobile navigation, keyboard focus states, a skip link, a motion toggle, reduced-motion support and a CSS pod fallback when WebGL is unavailable.

## Demonstration sequence

1. Open Try the response and leave Delhi selected.
2. Show the baseline: sample AQI 78, air agitation 25%, growth light 35%.
3. Select Simulate smog event. The sample AQI becomes 412.
4. Watch the ambient-reading, cloud-calculation, pod-response and classroom-alert stages.
5. At the pod-response stage, air agitation and growth light become 100%.
6. Inspect the classroom alert preview and export the manifest.
7. Return to baseline or reset the demonstration.

Everything in the console is a local simulation. It does not call an AQI API, send AWS messages, control hardware, store data in DynamoDB or send an SNS notification. Temperature is a sample value. The exported carbonReduction value is null because it has not been measured.

## Next integration steps

Add an authenticated backend/API Gateway route for air-quality readings and device commands. Keep credentials off the frontend. Wire Lambda control rules to IoT Core and an ESP32 device, then consume acknowledged device telemetry in the console. Use SNS for alerts and DynamoDB for event records. Add temperature sensing and define culture-specific safe limits before connecting the light/pump controls to living algae.

The current bottle prototype uses dyed water to demonstrate control behavior. CO2 uptake, PM2.5 capture and oxygen output need independent measurement. No 400× performance claim is made.

## References and assets

- Theme source: [Mohit Virli portfolio repository](https://github.com/mohitvirli/mohitvirli.github.io), pinned to commit edc716e10c120f5e19aa8358be433222a83d453e. The theme store, night-mode icon, star settings, background colors and grain come from his source. Original files and integration notes are in vendor/mohitvirli. The header toggle switches the opening between blue sky and a dark star field, themes the entire site and saves the selection in localStorage. Visible text is at least 16px, with larger body copy and shorter descriptions.
- Loader motion reference: [Buttermax](https://buttermax.net/). Their source uses a looping Lottie and shrink/fade exit; no proprietary Lottie asset is included here.
- Renderer: [React Three Fiber](https://github.com/pmndrs/react-three-fiber).
- Event: [Environmental Hacks](https://www.wemakedevs.org/aws/env). The event page specifies a recorded three-minute judging video.
- Fonts: [DM Sans](https://github.com/google/fonts/tree/main/ofl/dmsans) and [Instrument Serif](https://github.com/google/fonts/tree/main/ofl/instrumentserif), under the SIL Open Font License. License copies are in public/fonts.
- The supplied window GLB matches the Residential Window credited in the reference source: [AleixoAlonso](https://sketchfab.com/AleixoAlonso), [original model](https://sketchfab.com/3d-models/residential-window-ae11104237314463a61251fd46ded4b4), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Credits are linked in the footer and included in public/credits.txt.

## Checks

`npm run build` generates the static production site in dist/.

The Playwright suite checks the staged smog response, baseline recovery, city selection, AQI controls, manifest contents, reset cancellation, mobile navigation, intro replay, and desktop/mobile WebGL rendering. Start the local server on port 5173, then run `npm test`. If a browser is not installed, run `npx playwright install chromium` first. `PLAYWRIGHT_BASE_URL` can point the tests at another local port. Screenshots are saved in artifacts/.

Vite uses its native config loader and a workspace resolver because the managed Windows environment restricts esbuild's directory enumeration outside this folder. Off-screen scenes pause rendering.

## Opening journey

The first section spans five viewport heights and uses one sticky canvas. The title is rendered in 3D. The camera tilts downward, descends along the reference path, passes through the real GLB window, and then rotates upright for the AlgaeAir reveal. The handle and sash animate from the scroll position; reversing the scroll reverses the whole scene. The pod stays hidden until the camera has crossed the window plane. On mobile it moves below the introductory copy. `Explore the pod` skips to the reveal. Reduced motion keeps the sequence directly tied to scroll while stopping continuous floating animations. A CSS version handles devices without WebGL.

Run `npm run test:unit` for camera continuity and passage-order checks. The WebGL browser test captures the sky, clouds, opening window and pod on desktop and mobile, checks forward/backward passage through the window plane, and confirms the pod controls unlock at the reveal. UI interaction checks run separately from software WebGL rendering.
