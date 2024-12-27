from app.api.models import TagIn, TagOut, TagUpdate
from app.api.db import tags, database

async def add_tag(payload: TagIn): 
    #print(f"start add_tag word: {payload.name}")   
    query = tags.select(tags.c.name==payload.name)
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

async def get_all_tags():
    query = tags.select()
    return await database.fetch_all(query=query)

async def get_tag(id):
    query = tags.select(tags.c.id==id)
    return await database.fetch_one(query=query)

async def get_by_name(name):
    print(tags.c.name, name)
    query = tags.select(tags.c.name==name)
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
    return await database.execute(query=query)