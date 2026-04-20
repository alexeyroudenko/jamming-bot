```
http://localhost:8003/docs
```

```
http://localhost:8003/openapi.json
```

## New query filter

- `GET /api/v1/tags/tags/group/?count=50&page=0&days=0`
  - `days=0` (default) -> all-time counters from `movies`
  - `days=1,2,3...` -> aggregated counters for the last N UTC calendar days

## Backfill helper

- `POST /api/v1/tags/tags/backfill-daily/?dry_run=true&limit=0&offset=0`
  - pulls `storage-service` CSV export
  - parses `timestamp` + `tags`
  - fills `tag_daily_stats` when `dry_run=false`