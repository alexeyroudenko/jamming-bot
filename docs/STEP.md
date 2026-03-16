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

## Aggregated step (Redis hash `step:{number}`)

All job results are merged into a single Redis hash per step.
Base fields are written on arrival; each job appends its keys when it finishes.
TTL = `STEP_HASH_TTL` env var (default 3600s).

```
step:42 = {
  # base (from bot_service)
  number, url, src, ip, status_code, timestamp, text

  # do_geo  → event "location"
  city, latitude, longitude, error

  # analyze → event "analyzed"
  tags, words, hrases, entities, text_length

  # dostep  → event "tags_updated"
  semantic, semantic_words, semantic_hrases

  # do_screenshot → event "screenshot"
  screenshot_url, s3_key

  # do_storage → event "storage"
  storage
}
```

### API

```
GET /api/step/{number}/  →  full aggregated JSON
```
