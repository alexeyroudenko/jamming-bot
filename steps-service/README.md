# steps-service

FastAPI service that proxies `presence_raw.png`, renders it as a fullscreen background, and overlays metric-aware tooltip / auto-mode UI for `/steps/?type=...`.

## Environment

- `STEPS_IMAGE_URL` — source PNG URL, default `http://localhost:5000/api/storage_img/`
- `STEPS_LATEST_URL` — source latest-steps JSON URL, default `http://localhost:5000/api/storage_latest/`
- `STEPS_CSV_URL` — source CSV export used to build full step map for tooltip, default `http://storage_service:7781/export/csv`
- `STEPS_REFRESH_SECONDS` — image refresh interval in seconds, default `60`
- `STEPS_OUTPUT_DIR` — directory for cached `presence_raw.png`, default `/tmp/steps-service`

## Modes

- `status_code`
- `text_length`
- `timestamp_delta`
- `screenshot`
- `latitude_longitude`
- `error`

## Routes

- `GET /` — fullscreen HTML page with support for `?type=...`
- `GET /presence_raw.png` — latest proxied PNG snapshot
- `GET /api/latest` — cached full step payload aligned with current PNG
- `GET /healthz` — current image cache status
