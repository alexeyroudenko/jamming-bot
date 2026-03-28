## Context

- **Geo fields**: `STEP.md` documents `city`, `latitude`, `longitude`, `error` on each step; `do_geo` fills them via **ip-service**; values land in **storage-service** and are available through **`GET /api/storage_latest/`** (Flask proxy to `STORAGE_SERVICE_URL/get/latest`).
- **Existing WebGL pattern**: `tags_3d.html` uses **Three.js** from CDN + `OrbitControls`, full-viewport canvas, fetch JSON, error banners.
- **openspec CLI** may be absent locally; artifacts are hand-authored to match `schema: spec-driven` layout.

## Goals / Non-Goals

**Goals:**

- Ship a **globe view** (textured sphere or stylized wireframe + atmosphere) with **markers** at `(lat, lon)` for steps that parse to finite numbers.
- **Orbit + zoom** (mouse/touch where feasible); **hover or click** shows step id/number, city, URL snippet (from stored fields).
- **Performance**: cap plotted points (e.g. use latest N from API response, then subsample or aggregate if count is huge).
- Reuse **same auth/exposure** as other Flask pages (no new public data beyond what `/api/storage_latest/` already returns).

**Non-Goals:**

- Replacing **ip-service** or improving geo accuracy.
- **Real-time** Socket.IO stream of new points in MVP (optional follow-up).
- Full **React** port in the first slice (can be a later change under `frontend/`).

## Decisions

1. **Route**: `GET /geo/` or `GET /viz/geo/` — prefer **`/geo/`** for short bookmark; document in tasks.
2. **Renderer (target)**: Align with **[globe.gl US international outbound example](https://github.com/vasturiano/globe.gl/blob/master/example/airline-routes/us-international-outbound.html)** — **`globeImageUrl`** night Earth (`earth-night.jpg` via jsdelivr three-globe path), **points** (`pointColor`, `pointRadius`, `pointsMerge`, `pointAltitude`). Use **globe.gl** (ESM) or reproduce the same **texture + point styling** in Three.js. **Arcs** optional unless we add explicit “routes” semantics.
3. **Lat/lon → 3D**: standard **ECEF** or spherical placement:  
   `phi = (90 - lat) * DEG2RAD`, `theta = (lon + 180) * DEG2RAD`,  
   `x = -R * sin(phi) * cos(theta)`, `y = R * cos(phi)`, `z = R * sin(phi) * sin(theta)`  
   (verify handedness vs camera up = Y).
4. **Markers**: small **instanced meshes** or **Points** for many dots; for modest N, **SphereGeometry** clones or merged geometry — pick by performance in implementation.
5. **Data**: **`GET /api/storage_geo/`** returns `{ data: [ { number, ip, latitude, longitude, city } ] }` (Flask aggregates storage-service `/get/latest`, filters valid coords, optional `?limit=`). Globe page uses this endpoint; **`/api/storage_latest/`** acceptable temporary fallback during migration.
6. **CSP / assets**: match tags 3D (CDN); if CSP blocks textures, use **gradient sphere** without external texture URL.

## Risks / Trade-offs

- **Large payloads**: `/get/latest` can return thousands of rows — **client parse cost** and **draw calls**. Mitigation: limit to last K points in JS or add optional `?limit=` on proxy in a follow-up task.
- **Invalid/zero coords**: many steps may have `(0,0)` — treat as **invalid** unless explicitly allowed.
- **Overplotting**: same city stacks — optional **jitter** or **opacity** by count (follow-up).

## Migration Plan

1. Add Flask route + template; deploy app-service.  
2. No DB migration.  
3. **Rollback**: remove route, template, nav links.

## Open Questions

- Exact **max markers** default (e.g. 500–3000).  
- **`/api/storage_geo/`** is specified in `tasks.md` §8 (fields: `number`, `ip`, `latitude`, `longitude`, `city`). Add `url` to the payload later if tooltips need it without a second fetch.
