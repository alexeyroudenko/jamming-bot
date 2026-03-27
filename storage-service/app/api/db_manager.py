from sqlalchemy import desc, func, select
from app.api.db import steps, database

STEP_FIELDS = [
    'number', 'url', 'src', 'ip', 'status_code', 'timestamp', 'text',
    'city', 'latitude', 'longitude', 'error',
    'tags', 'words', 'hrases', 'entities', 'text_length',
    'semantic', 'semantic_words', 'semantic_hrases',
    'screenshot_url', 's3_key',
]


def _record_to_dict(r):
    if r is None:
        return None
    return {field: (str(r[field]) if r[field] is not None else '') for field in ['id'] + STEP_FIELDS}


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
    return _record_to_dict(row)


async def exists_batch(numbers: list[str]):
    query = select(steps.c.number).where(steps.c.number.in_(numbers))
    rows = await database.fetch_all(query=query)
    return {str(r["number"]) for r in rows}


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


async def get_latest(limit: int = 3000):
    total = await database.fetch_val(
        query=select(func.count()).select_from(steps)
    )

    query = steps.select().order_by(desc(steps.c.id)).limit(limit)
    rows = await database.fetch_all(query=query)
    result = [_record_to_dict(r) for r in reversed(rows)]
    return {
        "fields": STEP_FIELDS,
        "total_lines": total,
        "returned_lines": len(result),
        "data": result,
    }
