import json
import time

from sqlalchemy import and_, case, desc, func, select
from app.api.db import steps, steps_analysis, database

STEP_FIELDS = [
    'number', 'url', 'src', 'ip', 'status_code', 'timestamp', 'text',
    'city', 'latitude', 'longitude', 'error',
    'tags', 'words', 'hrases', 'entities', 'text_length',
    'semantic', 'semantic_words', 'semantic_hrases',
    'screenshot_url', 's3_key',
]

ANALYSIS_FIELDS = ['step_number', 'palette']
LATEST_ALLOWED_FIELDS = frozenset(['id'] + STEP_FIELDS + ['palette'])
DEFAULT_LATEST_FIELDS = STEP_FIELDS + ['palette']
_TOTAL_LINES_CACHE_TTL = 60.0
_total_lines_cache = {"value": None, "expires_at": 0.0}


def _record_to_dict(r, fields=None):
    if r is None:
        return None
    out_fields = fields if fields is not None else (['id'] + STEP_FIELDS)
    result = {}
    for field in out_fields:
        if field == 'palette':
            continue
        try:
            val = r[field]
        except (KeyError, IndexError):
            continue
        result[field] = str(val) if val is not None else ''
    return result


def _parse_latest_fields(fields):
    """Return (column_names_for_sql, include_palette, response_fields)."""
    if not fields:
        # Full row: id + STEP_FIELDS for SQL; response fields list matches legacy.
        return ['id'] + list(STEP_FIELDS), True, list(DEFAULT_LATEST_FIELDS)

    if isinstance(fields, str):
        requested = [f.strip() for f in fields.split(',') if f.strip()]
    else:
        requested = [str(f).strip() for f in fields if str(f).strip()]

    seen = set()
    ordered = []
    for name in requested:
        if name not in LATEST_ALLOWED_FIELDS or name in seen:
            continue
        seen.add(name)
        ordered.append(name)

    if not ordered:
        return ['id'] + list(STEP_FIELDS), True, list(DEFAULT_LATEST_FIELDS)

    include_palette = 'palette' in seen
    sql_names = [n for n in ordered if n != 'palette']
    # Always fetch number when palette is needed so we can join analysis rows.
    if include_palette and 'number' not in sql_names:
        sql_names.append('number')
    return sql_names, include_palette, ordered


async def _get_total_lines(include_total: bool = False):
    """Return total step count; refresh at most every TTL unless include_total."""
    now = time.monotonic()
    cached = _total_lines_cache["value"]
    fresh = cached is not None and now < _total_lines_cache["expires_at"]
    if fresh and not include_total:
        return cached
    total = await database.fetch_val(
        query=select(func.count()).select_from(steps)
    )
    _total_lines_cache["value"] = total
    _total_lines_cache["expires_at"] = now + _TOTAL_LINES_CACHE_TTL
    return total


def _analysis_record_to_dict(r):
    if r is None:
        return None
    palette_raw = r["palette"] if r["palette"] is not None else "[]"
    try:
        palette = json.loads(palette_raw)
    except (TypeError, ValueError):
        palette = []
    return {
        "id": r["id"],
        "step_number": str(r["step_number"]) if r["step_number"] is not None else "",
        "palette": palette if isinstance(palette, list) else [],
    }


async def get_stats():
    total_steps = await database.fetch_val(
        query=select(func.count()).select_from(steps)
    )
    return {"total_steps": total_steps}


async def add_step(data: dict):
    values = {f: str(data.get(f, '')) for f in STEP_FIELDS}
    query = steps.insert().values(**values)
    return await database.execute(query=query)


async def update_step(number: str, data: dict):
    values = {f: str(data[f]) for f in STEP_FIELDS if f in data and f != 'number'}
    if not values:
        return None
    query = steps.update().where(steps.c.number == number).values(**values)
    await database.execute(query=query)
    return await get_step_by_number(number)


async def get_step_by_number(number: str):
    query = steps.select().where(steps.c.number == number)
    row = await database.fetch_one(query=query)
    record = _record_to_dict(row)
    if not record:
        return None
    analysis = await get_step_analysis_by_number(number)
    record["palette"] = analysis["palette"] if analysis else []
    return record


async def upsert_step_analysis(step_number: str, palette: list[str]):
    existing = await get_step_analysis_by_number(step_number)
    values = {
        "step_number": str(step_number),
        "palette": json.dumps(list(palette or [])),
    }
    if existing:
        query = (
            steps_analysis.update()
            .where(steps_analysis.c.step_number == str(step_number))
            .values(**values)
        )
        await database.execute(query=query)
    else:
        query = steps_analysis.insert().values(**values)
        await database.execute(query=query)
    return await get_step_analysis_by_number(step_number)


async def get_step_analysis_by_number(step_number: str):
    query = steps_analysis.select().where(steps_analysis.c.step_number == str(step_number))
    row = await database.fetch_one(query=query)
    return _analysis_record_to_dict(row)


async def exists_batch(numbers: list[str]):
    query = select(steps.c.number).where(steps.c.number.in_(numbers))
    rows = await database.fetch_all(query=query)
    return {str(r["number"]) for r in rows}


def _parse_step_number(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


async def iter_all_steps(batch_size: int = 500):
    query = steps.select().order_by(steps.c.id)
    offset = 0
    while True:
        batch = await database.fetch_all(query=query.limit(batch_size).offset(offset))
        if not batch:
            break
        for r in batch:
            yield _record_to_dict(r)
        offset += batch_size


async def get_ids():
    query = select(steps.c.number)
    rows = await database.fetch_all(query=query)
    numbers = sorted(
        parsed for parsed in (_parse_step_number(r["number"]) for r in rows)
        if parsed is not None
    )
    return {"data": numbers}


async def get_max_step_number():
    """Cheap max step number for PNG cache invalidation (latest row by id)."""
    row = await database.fetch_one(
        query=select(steps.c.number).order_by(desc(steps.c.id)).limit(1)
    )
    if row is None:
        return None
    return _parse_step_number(row["number"])


def _image_columns(image_type: str):
    columns = [steps.c.id, steps.c.number]
    need_status = image_type in ("status_code",)
    need_timestamp = image_type in ("timestamp_delta",)
    need_text_length = image_type in ("text_length",)
    need_screenshot = image_type in ("screenshot",)
    need_geo = image_type in ("latitude_longitude",)
    if need_status:
        columns.append(steps.c.status_code)
    if need_timestamp:
        columns.append(steps.c.timestamp)
    if need_text_length:
        columns.append(steps.c.text_length)
    if need_screenshot:
        has_screenshot = case(
            (
                and_(
                    steps.c.screenshot_url.isnot(None),
                    steps.c.screenshot_url != "",
                ),
                1,
            ),
            else_=0,
        ).label("has_screenshot")
        columns.append(has_screenshot)
    if need_geo:
        columns.extend([steps.c.latitude, steps.c.longitude])
    return columns, need_status, need_timestamp, need_text_length, need_screenshot, need_geo


def _row_to_image_item(
    row,
    *,
    need_status,
    need_timestamp,
    need_text_length,
    need_screenshot,
    need_geo,
):
    number = _parse_step_number(row["number"])
    if number is None:
        return None
    item = {"number": number, "id": row["id"]}
    if need_status:
        item["status_code"] = str(row["status_code"] or "")
    if need_timestamp:
        item["timestamp"] = str(row["timestamp"] or "")
    if need_text_length:
        item["text_length"] = str(row["text_length"] or "")
    if need_screenshot:
        item["has_screenshot"] = int(row["has_screenshot"] or 0)
        item["screenshot_url"] = "1" if item["has_screenshot"] else ""
    if need_geo:
        item["latitude"] = str(row["latitude"] or "")
        item["longitude"] = str(row["longitude"] or "")
    return item


async def iter_image_row_batches(image_type: str = "status_code", batch_size: int = 15000):
    """
    Stream image rows in id-ordered batches (avoids loading all steps into RAM / killing Postgres).
    """
    batch_size = max(100, min(int(batch_size), 50000))
    columns, need_status, need_timestamp, need_text_length, need_screenshot, need_geo = (
        _image_columns(image_type)
    )
    last_id = 0
    while True:
        query = (
            select(*columns)
            .where(steps.c.id > last_id)
            .order_by(steps.c.id)
            .limit(batch_size)
        )
        rows = await database.fetch_all(query=query)
        if not rows:
            break
        batch = []
        for row in rows:
            item = _row_to_image_item(
                row,
                need_status=need_status,
                need_timestamp=need_timestamp,
                need_text_length=need_text_length,
                need_screenshot=need_screenshot,
                need_geo=need_geo,
            )
            if item is not None:
                batch.append(item)
            last_id = row["id"]
        if batch:
            yield batch
        if len(rows) < batch_size:
            break


async def get_image_rows(image_type: str = "status_code"):
    """Collect all image rows (prefer iter_image_row_batches for large tables)."""
    result = []
    async for batch in iter_image_row_batches(image_type):
        result.extend(batch)
    return result


async def get_latest(limit: int = 3000, fields=None, include_total: bool = False):
    sql_names, include_palette, response_fields = _parse_latest_fields(fields)
    columns = [steps.c[name] for name in sql_names if name in steps.c]
    if not columns:
        columns = [steps.c.id] + [steps.c[f] for f in STEP_FIELDS]

    total = await _get_total_lines(include_total=include_total)

    query = select(*columns).order_by(desc(steps.c.id)).limit(limit)
    rows = await database.fetch_all(query=query)
    # Dict keys for projected rows (exclude palette; added below when requested).
    dict_fields = [n for n in sql_names if n != 'palette']
    result = [_record_to_dict(r, fields=dict_fields) for r in reversed(rows)]

    if include_palette:
        numbers = [str(row.get("number", "")) for row in result if row.get("number")]
        analysis_map = {}
        if numbers:
            analysis_rows = await database.fetch_all(
                query=steps_analysis.select().where(
                    steps_analysis.c.step_number.in_(numbers)
                )
            )
            analysis_map = {
                str(r["step_number"]): (_analysis_record_to_dict(r) or {}).get("palette", [])
                for r in analysis_rows
            }
        for row in result:
            row["palette"] = analysis_map.get(str(row.get("number", "")), [])
        # Drop helper number if caller did not ask for it.
        if "number" not in response_fields:
            for row in result:
                row.pop("number", None)

    return {
        "fields": response_fields,
        "total_lines": total,
        "returned_lines": len(result),
        "data": result,
    }
