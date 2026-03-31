## step_data_structure:

```
number: int = step_number
url: str = ""
src: str = ""
ip: str = ""
status_code: int = 0
headers: str = ""
timestamp: str
text: str = ""
```

## do_geo:

```
location = {'ip': ip, 'city': '', 'latitude': 0, 'longitude': 0, 'error': ''}
```

## do_analyze:

```
analyzes = {"tags": tags,"hrases": hrases,"entities": entities}
```

## Canonical field order (STEP_FIELDS)

All storage writes use this fixed column order.
Defined in `jobs.py:STEP_FIELDS` and `storage-service/app/main.py:STEP_FIELDS`.

```
number, url, src, ip, status_code, timestamp, text,
city, latitude, longitude, error,
tags, words, hrases, entities, text_length,
semantic, semantic_words, semantic_hrases,
screenshot_url, s3_key
```

## Aggregated step (Redis hash `step:{number}`)

All job results are merged into a single Redis hash per step.
Base fields are written on arrival; each job appends its keys when it finishes.
TTL = `STEP_HASH_TTL` env var (default 3600s).

After all jobs complete, `do_storage` sends the full ordered payload
to storage-service, which writes it as TSV + individual JSON file.

### API

```
GET /api/step/{number}/          → from Redis hash (live, TTL 1h)
GET /api/storage_step/{number}/  → from storage-service JSON (persistent)
GET /api/storage_latest/         → last 3000 steps with named fields
GET /api/storage_ids/            → all stored step numbers sorted ascending
```
