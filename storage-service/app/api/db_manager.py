import json

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


def _record_to_dict(r):
    if r is None:
        return None
    return {field: (str(r[field]) if r[field] is not None else '') for field in ['id'] + STEP_FIELDS}


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


async def get_latest(limit: int = 3000):
    total = await database.fetch_val(
        query=select(func.count()).select_from(steps)
    )

    query = steps.select().order_by(desc(steps.c.id)).limit(limit)
    rows = await database.fetch_all(query=query)
    result = [_record_to_dict(r) for r in reversed(rows)]
    analysis_rows = await database.fetch_all(query=steps_analysis.select())
    analysis_map = {
        str(r["step_number"]): (_analysis_record_to_dict(r) or {}).get("palette", [])
        for r in analysis_rows
    }
    for row in result:
        row["palette"] = analysis_map.get(str(row.get("number", "")), [])
    return {
        "fields": STEP_FIELDS + ["palette"],
        "total_lines": total,
        "returned_lines": len(result),
        "data": result,
    }
