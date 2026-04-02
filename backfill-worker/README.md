# backfill-worker

One-shot job: loads visited URLs from data-service page by page, skips IDs already in storage-service, fetches HTML and posts silent steps to app-service.

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_SERVICE_URL` | `http://data-service` | Base URL of data-service |
| `STORAGE_SERVICE_URL` | `http://storage-service` | Base URL of storage-service |
| `APP_SERVICE_URL` | `http://app-service` | Base URL of app-service (Flask) |
| `BATCH_SIZE` | `100` | Rows per data-service page |
| `SLEEP_BETWEEN` | `2.0` | Seconds between processed URLs (fallback if Redis key missing) |
| `PAGE_TIMEOUT` | `10` | HTTP fetch timeout in seconds (fallback if Redis key missing) |
| `BACKFILL_URL_ORDER` | `round_robin` | `round_robin` — shuffle within hostname, interleave hosts per batch; `id` — same order as data-service (`ORDER BY id`) |
| `BACKFILL_STEP_BASE` | `100000` | Step number offset for writes to app/storage (`step_number = BACKFILL_STEP_BASE + source id`); set `0` to keep step numbers equal to source id |
| `BACKFILL_MIN_ID` | `0` | Lower inclusive bound for source `id` processed by backfill (e.g. `1`) |
| `BACKFILL_MAX_ID` | `2147483647` | Upper inclusive bound for source `id` processed by backfill (e.g. `300000`) |
| `BACKFILL_RANDOM_SEED` | _(empty)_ | If set, passed to `random.seed()` for reproducible shuffles |
| `REDIS_HOST` / `REDIS_PORT` | `redis` / `6379` | Status hash for `/api/backfill/status/` |
| `BACKFILL_STATUS_KEY` | `backfill:status` | Redis hash key |

## Redis tuning (from `/ctrl/`)

If keys exist, they override env defaults for the running worker:

| Key | Default (set by Flask `_ensure_redis_defaults`) | Effect |
|-----|--------------------------------------------------|--------|
| `backfill_sleep` | `2.0` | Pause after each processed URL (seconds, min 0) |
| `backfill_timeout` | `4.0` | Per-request HTTP timeout (seconds; `0` or negative → treated as 1 s) |
