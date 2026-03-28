## 1. Flask route and template

- [x] 1.1 Add `GET /geo/` in `app-service/flask/app.py` rendering `geo_globe.html` (name may match template)
- [x] 1.2 Create `app-service/flask/templates/geo_globe.html` with nav, WebGL canvas container, status/error DOM hooks

## 2. Assets and globe baseline

- [x] 2.1 Add Three.js (+ OrbitControls) via CDN consistent with `tags_3d.html` (SRI if used elsewhere)
- [x] 2.2 Implement Earth sphere (textured or solid/emissive material); add subtle lighting or unlit material as needed

## 3. Data and geo mapping

- [x] 3.1 `fetch('/api/storage_latest/')`, parse `data` / `data.data` shape returned by proxy (align with actual JSON)
- [x] 3.2 Filter rows: parse `latitude`/`longitude` as numbers; skip invalid, NaN, or (0,0) if treated as unknown
- [x] 3.3 Map lat/lon to 3D positions on sphere radius R; place markers (mesh or points)
- [x] 3.4 Cap max markers (e.g. 1500–3000 or newest-first slice); document constant in template

## 4. Interaction and UX

- [x] 4.1 OrbitControls: damping, min/max distance suitable for globe scale
- [x] 4.2 Raycast pick or hover: show step `number`, `city`, `url` (truncate in UI)
- [x] 4.3 On API error / empty geo set, show visible banner; empty valid points → explanatory message

## 5. Navigation

- [x] 5.1 Add link to `/geo/` from `bot.html` (and optionally `tags.html` or `screenshots.html` nav)
- [x] 5.2 Geo page links: home (`/`), optional tags/screenshots

## 6. Verify

- [ ] 6.1 Manual test with storage containing diverse lat/lon
- [ ] 6.2 Manual test: API down, WebGL disabled, empty geo list

## 7. Optional follow-ups (superseded / see §8–9)

- [ ] 7.1 ~~`GET /api/geo_points/?limit=`~~ — use **`/api/storage_geo/`** in §8 instead (fields: `number`, `ip`, `latitude`, `longitude`, `city`)
- [ ] 7.2 Mirror route in `frontend/` SPA if product standard moves to React for all viz pages

## 8. Slim geo API (`/api/storage_geo/`)

- [x] 8.1 Add **`GET /api/storage_geo/`** in `app-service/flask/app.py` that returns JSON whose **records** include exactly these fields (names as below): **`number`**, **`ip`**, **`latitude`**, **`longitude`**, **`city`** (types: string/number consistent with storage-service; omit or filter rows without valid non-zero lat/lon using the same rules as `/geo/` page)
- [x] 8.2 Implement by aggregating from **storage-service** via existing `GET /get/latest` (or dedicated slim query later); support optional **`?limit=`** (default e.g. 2000, newest-first by step id/number)
- [x] 8.3 Response shape: e.g. `{ "data": [ { "number", "ip", "latitude", "longitude", "city" }, ... ] }` — document in code comment
- [x] 8.4 Add **`/api/storage_geo/`** to **`PUBLIC_PREFIXES`** so the globe works without session (same policy as `/api/storage_latest/`)

## 9. Globe visuals — [globe.gl airline-routes example](https://github.com/vasturiano/globe.gl/blob/master/example/airline-routes/us-international-outbound.html)

Reference example uses **`Globe`** from **globe.gl** with:

- **`globeImageUrl`** — night Earth texture, e.g. `//cdn.jsdelivr.net/npm/three-globe/example/img/earth-night.jpg` (or equivalent CDN URL with scheme)
- **Points layer**: `pointColor` (e.g. orange), `pointRadius`, `pointAltitude` (0 on surface), `pointsMerge(true)`
- **Arcs** — animated dashed arcs between endpoints; **optional** for Jamming Bot unless we visualize explicit “routes” between steps (default: **points-only** unless product asks for arcs)

Tasks:

- [x] 9.1 Replace or augment `geo_globe.html` so the **Earth surface** matches the example’s **night texture** look (via **globe.gl** ESM bundle from jsdelivr / unpkg, or Three.js sphere with the **same** `earth-night.jpg` texture)
- [x] 9.2 Style **markers** like the example’s **airports point layer** (color, relative size, merged points if using globe.gl)
- [x] 9.3 Switch data source from `/api/storage_latest/` to **`/api/storage_geo/`** once §8 is done (smaller payload); keep hover/label fields available (may extend API with `url` later if needed for tooltip)
- [x] 9.4 Set initial **`pointOfView`** / camera aim similar in spirit to the example (e.g. sensible altitude and lat/lng over area of interest); document constant in template
