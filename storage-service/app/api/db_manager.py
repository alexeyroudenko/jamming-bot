import json
import time

from sqlalchemy import desc, func, select
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


async def get_image_rows():
    query = select(
        steps.c.number,
        steps.c.status_code,
        steps.c.timestamp,
        steps.c.text_length,
        steps.c.screenshot_url,
    )
    rows = await database.fetch_all(query=query)
    result = []
    for row in rows:
        number = _parse_step_number(row["number"])
        if number is None:
            continue
        result.append({
            "number": number,
            "status_code": str(row["status_code"] or ""),
            "timestamp": str(row["timestamp"] or ""),
            "text_length": str(row["text_length"] or ""),
            "screenshot_url": str(row["screenshot_url"] or ""),
        })
    result.sort(key=lambda item: item["number"])
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
