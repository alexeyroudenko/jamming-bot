import csv
import io
import math
import struct
from typing import List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from starlette.status import HTTP_400_BAD_REQUEST
from pydantic import BaseModel
from app.api.db import metadata, database, engine
from app.api import db_manager
from app.api.models import StepAnalysisIn
import asyncio
import logging
import os
import zlib

logger = logging.getLogger("storage_service")
logging.basicConfig(level=logging.INFO)

app = FastAPI()


def _choose_presence_dimensions(max_step_id: int, requested_width: int) -> tuple[int, int]:
    if requested_width and requested_width > 0:
        width = requested_width
    else:
        width = max(1, math.ceil(math.sqrt(max_step_id + 1)))
    height = max(1, math.ceil((max_step_id + 1) / width))
    return width, height


def _rasterize_presence(step_ids: list[int], width: int, height: int) -> list[bytearray]:
    rows = [bytearray(width) for _ in range(height)]
    for step_id in step_ids:
        x = step_id % width
        y = step_id // width
        if y < height:
            rows[y][x] = 255
    return rows


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack("!I", len(data))
        + tag
        + data
        + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def _build_grayscale_png(rows: list[bytearray], width: int, height: int) -> bytes:
    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    header = struct.pack("!2I5B", width, height, 8, 0, 0, 0, 0)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            _png_chunk(b"IHDR", header),
            _png_chunk(b"IDAT", zlib.compress(raw, level=9)),
            _png_chunk(b"IEND", b""),
        ]
    )


async def _init_db_with_retry():
    max_attempts = int(os.getenv("DB_INIT_MAX_ATTEMPTS", "15"))
    delay = float(os.getenv("DB_INIT_DELAY_SECONDS", "2"))
    for attempt in range(1, max_attempts + 1):
        try:
            metadata.create_all(engine)
            logger.info("Database initialization successful on attempt %s", attempt)
            return
        except Exception as e:
            if attempt == max_attempts:
                logger.error("Database initialization failed after %s attempts: %s", attempt, e)
                raise
            logger.warning("DB not ready (attempt %s/%s): %s; retrying in %.1fs",
                           attempt, max_attempts, e, delay)
            await asyncio.sleep(delay)


@app.on_event("startup")
async def startup():
    await _init_db_with_retry()
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.post("/store")
async def store(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Invalid or empty JSON body"
        )
    if not isinstance(data, dict) or not data:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="JSON body must be a non-empty object"
        )

    await db_manager.add_step(data)
    return {"msg": "ok"}


@app.patch("/update/step/{number}")
async def update_step(number: str, request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Invalid or empty JSON body"
        )
    existing = await db_manager.get_step_by_number(number)
    if not existing:
        raise HTTPException(status_code=404, detail="Step not found")
    updated = await db_manager.update_step(number, data)
    return updated


class ExistsBatchRequest(BaseModel):
    numbers: List[str]


@app.post("/exists/batch")
async def exists_batch(payload: ExistsBatchRequest):
    existing = await db_manager.exists_batch(payload.numbers)
    missing = [n for n in payload.numbers if n not in existing]
    return {"existing": list(existing), "missing": missing}


@app.get("/get/step/{number}")
async def get_step(number: str):
    step = await db_manager.get_step_by_number(number)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    return step


@app.get("/get/latest")
async def get_latest():
    return await db_manager.get_latest()


@app.post("/analysis/store")
async def store_step_analysis(payload: StepAnalysisIn):
    result = await db_manager.upsert_step_analysis(payload.step_number, payload.palette)
    return result


@app.get("/analysis/get/{number}")
async def get_step_analysis(number: str):
    analysis = await db_manager.get_step_analysis_by_number(number)
    if not analysis:
        raise HTTPException(status_code=404, detail="Step analysis not found")
    return analysis


@app.get("/get/ids")
async def get_ids():
    return await db_manager.get_ids()


@app.get("/export/csv")
async def export_csv():
    async def _generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        fields = ['id'] + db_manager.STEP_FIELDS
        writer.writerow(fields)
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        async for row in db_manager.iter_all_steps():
            writer.writerow([row.get(f, '') for f in fields])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    return StreamingResponse(
        _generate(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="steps_export.csv"'},
    )


@app.get("/export/img")
async def export_img(width: int = 0):
    payload = await db_manager.get_ids()
    step_ids = payload.get("data", [])
    if not step_ids:
        raise HTTPException(status_code=404, detail="No step ids available")

    max_step_id = step_ids[-1]
    img_width, img_height = _choose_presence_dimensions(max_step_id, width)
    rows = _rasterize_presence(step_ids, img_width, img_height)
    png_bytes = _build_grayscale_png(rows, img_width, img_height)

    return StreamingResponse(
        io.BytesIO(png_bytes),
        media_type="image/png",
        headers={"Content-Disposition": 'inline; filename="presence_raw.png"'},
    )
