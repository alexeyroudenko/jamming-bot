from app.api.models import TagIn, TagOut, TagUpdate
from app.api.db import tags, database

async def add_tag(payload: TagIn): 
    #print(f"start add_tag word: {payload.name}")   
    query = tags.select().where(tags.c.name == payload.name)
    result = await database.fetch_all(query=query)
    if len(result) > 0:        
        id = int(result[0]['id'])
        name = str(result[0]['name'])
        count = int(result[0]['count'])
        payload.count = count + 1    
        query = (
            tags
            .update()
            .where(tags.c.id == id)
            .values(**payload.dict())
        )
        await database.execute(query=query)
        return id
    else:
        query = tags.insert().values(**payload.dict())
        return await database.execute(query=query)

def _record_to_dict(r):
    """Convert a databases Record to a plain dict so 'count' column doesn't clash with Sequence.count()."""
    if r is None:
        return None
    return {"id": int(r["id"]), "name": str(r["name"]) if r["name"] else "", "count": int(r["count"]) if r["count"] is not None else 0}

async def get_all_tags():
    query = tags.select()
    rows = await database.fetch_all(query=query)
    return [_record_to_dict(r) for r in rows]

async def get_tag(id):
    query = tags.select().where(tags.c.id == id)
    return _record_to_dict(await database.fetch_one(query=query))

async def get_by_name(name):
    print(tags.c.name, name)
    query = tags.select().where(tags.c.name == name)
    return await database.fetch_all(query=query)

async def delete_tag(id: int):
    query = tags.delete().where(tags.c.id==id)
    return await database.execute(query=query)

async def update_tag(id: int, payload: TagIn):
    query = (
        tags
        .update()
        .where(tags.c.id == id)
        .values(**payload.dict())
    )
    await database.execute(query=query)
    return await get_tag(id)


async def get_grouped_tags():
    from sqlalchemy import desc
    query = (
        tags.select()
        .order_by(desc(tags.c.count))
        .limit(150)
    )
    rows = await database.fetch_all(query=query)
    return [_record_to_dict(r) for r in rows]
