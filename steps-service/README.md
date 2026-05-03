# steps-service

FastAPI service that proxies step PNG snapshots, renders them as a fullscreen background, and overlays metric-aware tooltip / auto-mode UI for `/steps/?type=...`.

## Environment

- `STEPS_IMAGE_URL` — source PNG URL, default `http://localhost:5000/api/storage_img/`
- `STEPS_LATEST_URL` — source latest-steps JSON URL (preferred for refresh), default `http://localhost:5000/api/storage_latest/`
- `STEPS_LATEST_LIMIT` — max rows requested from latest (`?limit=`), default `3000`, capped at `20000`
- `STEPS_CSV_URL` — CSV export used only if latest JSON fails, default `http://storage_service:7781/export/csv`
- `STEPS_REFRESH_SECONDS` — background refresh interval in seconds, default `60`
- `STEPS_OUTPUT_DIR` — directory for cached step PNG snapshots, default `/tmp/steps-service`

Background refresh loads only the **default** presence PNG (`status_code`) plus step rows from **latest JSON** (not full CSV unless latest fails). Other PNG modes are fetched on demand when the UI requests `/api/image`.

## Modes

- `status_code`
- `text_length`
- `timestamp_delta`
- `screenshot`
- `latitude_longitude`
- `error`

## Routes

- `GET /` — fullscreen HTML page with support for `?type=...`
- `GET /api/image` — latest proxied PNG snapshot
- `GET /api/latest` — cached full step payload (debug/compat endpoint, not required by `/steps` UI)
- `GET /healthz` — current image cache status (diagnostics)
- `GET /live` — instant liveness (Kubernetes)
- `GET /ready` — readiness when default snapshot is loaded (`503` while warming up)

## Backfill panel

The page includes a collapsible **Backfill** panel that polls `GET /api/backfill/status/` on the **same browser origin** (e.g. main host serves `/steps` via this service and `/api/*` via app-service). If Steps is ever served from another origin, configure CORS or a reverse-proxy for that API.

