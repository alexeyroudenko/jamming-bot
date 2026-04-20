import ast
import csv
import io
import json
from datetime import datetime, timezone, timedelta

import httpx
from sqlalchemy import and_, desc, func, select

from app.api.models import TagIn, TagOut, TagUpdate
from app.api.db import database, tag_daily_stats, tags

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
        await increment_daily_tag_count(payload.name)
        return id
    else:
        query = tags.insert().values(**payload.dict())
        new_id = await database.execute(query=query)
        await increment_daily_tag_count(payload.name)
        return new_id

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


async def add_tags_bulk(raw_names: list) -> dict:
    """Для каждого имени вызывает add_tag(TagIn(...)) — порядок и дубликаты как у серии одиночных POST."""
    skipped_empty = 0
    processed = 0
    errors: list = []
    for raw in raw_names:
        name = str(raw).strip()[:50]
        if not name:
            skipped_empty += 1
            continue
        try:
            await add_tag(TagIn(name=name, count=0))
            processed += 1
        except Exception as e:
            errors.append({"name": name, "error": str(e)})
    out = {
        "ok": len(errors) == 0,
        "processed": processed,
        "skipped_empty": skipped_empty,
        "input_count": len(raw_names),
    }
    if errors:
        out["errors"] = errors
    return out


async def sync_tags_bulk(items: list) -> dict:
    """Upsert tags with exact count values (for sync from remote)."""
    created = 0
    updated = 0
    errors: list = []
    for item in items:
        name = str(item.get("name", "")).strip()[:50]
        count = int(item.get("count", 0))
        if not name:
            continue
        try:
            query = tags.select().where(tags.c.name == name)
            result = await database.fetch_all(query=query)
            if result:
                existing_id = int(result[0]["id"])
                query = (
                    tags.update()
                    .where(tags.c.id == existing_id)
                    .values(name=name, count=count)
                )
                await database.execute(query=query)
                updated += 1
            else:
                query = tags.insert().values(name=name, count=count)
                await database.execute(query=query)
                created += 1
        except Exception as e:
            errors.append({"name": name, "error": str(e)})
    out = {
        "ok": len(errors) == 0,
        "created": created,
        "updated": updated,
        "input_count": len(items),
    }
    if errors:
        out["errors"] = errors
    return out


async def get_stats():
    total = await database.fetch_val(
        query=select(func.count()).select_from(tags)
    )
    return {"total": total}


def _safe_tag_name(raw):
    return str(raw or "").strip()[:50]


def _parse_step_timestamp_to_utc_date(raw_ts):
    if raw_ts is None:
        return None
    text = str(raw_ts).strip()
    if not text:
        return None
    try:
        seconds = float(text)
        return datetime.fromtimestamp(seconds, tz=timezone.utc).date()
    except (TypeError, ValueError, OSError):
        return None


def _parse_step_tags(raw_tags):
    if raw_tags is None:
        return []
    if isinstance(raw_tags, list):
        return [_safe_tag_name(x) for x in raw_tags if _safe_tag_name(x)]
    text = str(raw_tags).strip()
    if not text:
        return []
    parsed = None
    try:
        parsed = json.loads(text)
    except Exception:
        try:
            parsed = ast.literal_eval(text)
        except Exception:
            parsed = None
    if isinstance(parsed, list):
        return [_safe_tag_name(x) for x in parsed if _safe_tag_name(x)]
    return []


async def increment_daily_tag_count(tag_name: str, day=None, increment: int = 1):
    safe_tag_name = _safe_tag_name(tag_name)
    if not safe_tag_name:
        return
    target_day = day or datetime.now(timezone.utc).date()
    query = (
        tag_daily_stats.select()
        .where(
            and_(
                tag_daily_stats.c.day == target_day,
                tag_daily_stats.c.tag_name == safe_tag_name,
            )
        )
    )
    row = await database.fetch_one(query=query)
    if row:
        update_query = (
            tag_daily_stats.update()
            .where(tag_daily_stats.c.id == row["id"])
            .values(count=int(row["count"] or 0) + int(increment))
        )
        await database.execute(query=update_query)
        return
    insert_query = tag_daily_stats.insert().values(
        day=target_day,
        tag_name=safe_tag_name,
        count=max(0, int(increment)),
    )
    await database.execute(query=insert_query)


def _grouped_row_to_dict(r, with_total=False):
    if r is None:
        return None
    payload = {
        "id": int(r["id"]) if r["id"] is not None else 0,
        "name": str(r["name"]) if r["name"] else "",
        "count": int(r["count"]) if r["count"] is not None else 0,
    }
    if with_total:
        payload["total_count"] = int(r["total_count"]) if r["total_count"] is not None else 0
    return payload


async def get_grouped_tags(count: int = 50, page: int = 0, days: int = 0):
    safe_count = max(1, min(500, int(count)))
    safe_page = max(0, int(page))
    safe_days = max(0, int(days))
    if safe_days > 0:
        cutoff_day = datetime.now(timezone.utc).date() - timedelta(days=safe_days - 1)
        daily_agg_subquery = (
            select(
                tag_daily_stats.c.tag_name.label("name"),
                func.sum(tag_daily_stats.c.count).label("total_count"),
            )
            .where(tag_daily_stats.c.day >= cutoff_day)
            .group_by(tag_daily_stats.c.tag_name)
            .subquery()
        )
        query = (
            select(
                func.coalesce(tags.c.id, 0).label("id"),
                daily_agg_subquery.c.name.label("name"),
                daily_agg_subquery.c.total_count.label("count"),
            )
            .select_from(
                daily_agg_subquery.outerjoin(tags, tags.c.name == daily_agg_subquery.c.name)
            )
            .order_by(desc(daily_agg_subquery.c.total_count), daily_agg_subquery.c.name.asc())
            .limit(safe_count)
            .offset(safe_page * safe_count)
        )
        rows = await database.fetch_all(query=query)
        return [_grouped_row_to_dict(r) for r in rows]
    query = (
        tags.select()
        .order_by(desc(tags.c.count), tags.c.name.asc())
        .limit(safe_count)
        .offset(safe_page * safe_count)
    )
    rows = await database.fetch_all(query=query)
    return [_record_to_dict(r) for r in rows]


async def backfill_daily_from_storage(storage_url: str, limit: int = 0, offset: int = 0, dry_run: bool = True):
    safe_limit = max(0, int(limit))
    safe_offset = max(0, int(offset))
    processed_steps = 0
    used_steps = 0
    skipped_steps = 0
    tag_increments = 0

    row_iter = None
    try:
        latest_limit = max(100, safe_limit + safe_offset) if safe_limit else 3000
        async with httpx.AsyncClient(timeout=45) as client:
            latest_response = await client.get(
                f"{storage_url.rstrip('/')}/get/latest",
                params={"limit": latest_limit},
            )
            latest_response.raise_for_status()
            latest_rows = latest_response.json()
            if isinstance(latest_rows, list):
                row_iter = latest_rows
            elif isinstance(latest_rows, dict) and isinstance(latest_rows.get("data"), list):
                row_iter = latest_rows.get("data")
    except Exception:
        row_iter = None

    if row_iter is None:
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.get(f"{storage_url.rstrip('/')}/export/csv")
                response.raise_for_status()
                csv_text = response.text
            row_iter = csv.DictReader(io.StringIO(csv_text))
        except Exception as exc:
            return {
                "ok": False,
                "dry_run": bool(dry_run),
                "error": f"storage fetch failed: {exc}",
                "storage_url": storage_url,
                "limit": safe_limit,
                "offset": safe_offset,
            }

    for idx, row in enumerate(row_iter):
        if idx < safe_offset:
            continue
        if safe_limit and processed_steps >= safe_limit:
            break
        processed_steps += 1

        step_day = _parse_step_timestamp_to_utc_date(row.get("timestamp"))
        step_tags = _parse_step_tags(row.get("tags"))
        if not step_day or not step_tags:
            skipped_steps += 1
            continue
        used_steps += 1
        if not dry_run:
            for name in step_tags:
                await increment_daily_tag_count(name, day=step_day, increment=1)
                tag_increments += 1
        else:
            tag_increments += len(step_tags)

    return {
        "ok": True,
        "dry_run": bool(dry_run),
        "processed_steps": processed_steps,
        "used_steps": used_steps,
        "skipped_steps": skipped_steps,
        "tag_increments": tag_increments,
        "limit": safe_limit,
        "offset": safe_offset,
    }
