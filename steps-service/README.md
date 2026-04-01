# steps-service

FastAPI service that renders step presence into `presence_raw.png`, serves it as a fullscreen HTML background, and returns step ids for hovered pixels.

## Environment

- `STEPS_STORAGE_IDS_URL` — source endpoint for step ids, default `http://storage_service:7781/get/ids`
- `STEPS_REFRESH_SECONDS` — refresh interval in seconds, default `60`
- `STEPS_OUTPUT_DIR` — directory for `presence_raw.png` and metadata, default `/tmp/steps-service`
- `STEPS_CANVAS_WIDTH` — optional fixed canvas width, default automatic

## Routes

- `GET /` — fullscreen HTML page
- `GET /presence_raw.png` — latest PNG snapshot
- `GET /api/tooltip?x=...&y=...` — hovered step id or `null`
- `GET /healthz` — current render status
