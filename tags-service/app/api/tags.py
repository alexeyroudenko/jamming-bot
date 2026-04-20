from typing import List
import os
from fastapi import APIRouter, HTTPException, Query

from app.api.models import TagOut, TagIn, TagUpdate, TagBulkIn, TagSyncIn
from app.api import db_manager
from app.api.service import is_cast_present

tags = APIRouter()
STORAGE_SERVICE_URL = os.getenv("STORAGE_SERVICE_URL", "http://storage_service:8001")

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

@tags.get('/stats')
async def get_stats():
    return await db_manager.get_stats()


@tags.get('/', response_model=List[TagOut])
async def get_tags():
    return await db_manager.get_all_tags()


@tags.post('/bulk/', status_code=200)
async def create_tags_bulk(payload: TagBulkIn):
    """Несколько тегов за один запрос; семантика как у повторных POST /."""
    return await db_manager.add_tags_bulk(payload.names)


@tags.post('/sync/', status_code=200)
async def sync_tags(payload: TagSyncIn):
    """Upsert tags with exact count values (for sync from remote)."""
    return await db_manager.sync_tags_bulk([item.dict() for item in payload.items])


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
async def get_tags_group(
    count: int = Query(50, ge=1),
    page: int = Query(0, ge=0),
    days: int = Query(0, ge=0),
):
    return await db_manager.get_grouped_tags(count=count, page=page, days=days)


@tags.post('/tags/backfill-daily/', status_code=200)
async def backfill_daily_tags(
    dry_run: bool = Query(True),
    limit: int = Query(0, ge=0),
    offset: int = Query(0, ge=0),
):
    """
    Build per-day tag counters from storage-service CSV export.
    dry_run=true reports counts without writing.
    """
    return await db_manager.backfill_daily_from_storage(
        storage_url=STORAGE_SERVICE_URL,
        limit=limit,
        offset=offset,
        dry_run=dry_run,
    )
