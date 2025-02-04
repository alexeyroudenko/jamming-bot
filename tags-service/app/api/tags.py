from typing import List
from fastapi import APIRouter, HTTPException

from app.api.models import TagOut, TagIn, TagUpdate #, TagGetAndUpdate
from app.api import db_manager
from app.api.service import is_cast_present

tags = APIRouter()

@tags.post('/', response_model=TagOut, status_code=201)
async def create_tag(payload: TagIn):
    # for cast_id in payload.casts_id:
        # if not is_cast_present(cast_id):
            # raise HTTPException(status_code=404, detail=f"Cast with given id:{tag_id} not found")

    tag_id = await db_manager.add_tag(payload)
    response = {
        'id': tag_id,
        **payload.dict()
    }

    return response

@tags.get('/', response_model=List[TagOut])
async def get_tags():
    return await db_manager.get_all_tags()

@tags.get('/{id}/', response_model=TagOut)
async def get_tag(id: int):
    tag = await db_manager.get_tag(id)
    if not tag:
        raise HTTPException(status_code=404, detail="tag not found")
    return tag

@tags.put('/{id}/', response_model=TagOut)
async def update_tag(id: int, payload: TagUpdate):
    tag = await db_manager.get_tag(id)
    if not tag:
        raise HTTPException(status_code=404, detail="tag not found")

    update_data = payload.dict(exclude_unset=True)

    # if 'casts_id' in update_data:
    #     for cast_id in payload.casts_id:
    #         if not is_cast_present(cast_id):
    #             raise HTTPException(status_code=404, detail=f"Cast with given id:{cast_id} not found")

    tags_in_db = TagIn(**tag)

    updated_tag = tags_in_db.copy(update=update_data)

    return await db_manager.update_tag(id, updated_tag)

@tags.delete('/{id}/', response_model=None)
async def delete_tag(id: int):
    tag = await db_manager.get_tag(id)
    if not tag:
        raise HTTPException(status_code=404, detail="tag not found")
    return await db_manager.delete_tag(id)



@tags.get('/tags/group/', response_model=List[TagOut])
async def get_tags_group():
    return await db_manager.get_grouped_tags()
