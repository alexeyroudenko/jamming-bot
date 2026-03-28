## Why

Steps already carry **geolocation** from the IP/geo pipeline (`city`, `latitude`, `longitude` in storage and `STEP_FIELDS`). There is no dedicated map or globe view to **see where crawled hosts cluster** in the world. A **WebGL globe** gives an intuitive, visual summary of geographic distribution and complements tag/semantic dashboards.

## What Changes

- Add a **geo visualization page** that renders a **3D globe** (WebGL) and plots **points** (optional **arcs** later) for steps that have valid coordinates.
- **Data source (target)**: **`GET /api/storage_geo/`** returning slim records: **`number`**, **`ip`**, **`latitude`**, **`longitude`**, **`city`** (Flask aggregates storage-service; public prefix like `storage_latest`). Until implemented, the page may use **`/api/storage_latest/`** as fallback.
- **Globe look**: align with **[globe.gl US international outbound example](https://github.com/vasturiano/globe.gl/blob/master/example/airline-routes/us-international-outbound.html)** — **night Earth** texture, **point** styling (e.g. orange merged points); implement via **globe.gl** or equivalent Three.js + same assets.
- **Navigation**: link from `bot.html` and/or a small nav block consistent with `/tags/` and `/tags/3d/`.
- **Fallback**: clear message if WebGL fails or API errors; nav remains usable.

## Capabilities

### New Capabilities

- `geo-globe-page`: User-facing WebGL globe page: data binding from storage latest steps, rendering rules for geo points, interaction (orbit/zoom, optional hover/tooltip), performance bounds, and navigation.

### Modified Capabilities

- _(none — baseline specs under `openspec/specs/` remain unchanged unless we later merge this change)_

## Impact

- **app-service**: `/geo/` template; **`GET /api/storage_geo/`** (+ **`PUBLIC_PREFIXES`** entry); globe assets (**globe.gl** ESM or Three.js + **earth-night** texture from jsdelivr / three-globe path).
- **Frontend**: optional follow-up route in React app is **out of scope** unless tasks add it; default remains Flask template.
- **storage-service**: no schema change; **read** via existing `/get/latest` behind Flask (or future slim endpoint if added).
- **Privacy**: visualization shows **approximate geo from IP lookup** already stored in the product; document that in UX copy if needed.
