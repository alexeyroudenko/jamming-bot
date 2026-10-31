import asyncio
import csv
import io
import logging
import math
import os
import struct
import time
import zlib
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from starlette.status import HTTP_400_BAD_REQUEST

from app.api import db_manager
from app.api.db import database, engine, metadata
from app.api.models import StepAnalysisIn

logger = logging.getLogger("storage_service")
logging.basicConfig(level=logging.INFO)
BACKFILL_IMAGE_PATH = os.getenv("BACKFILL_IMAGE_PATH", "/tmp/backfill/presence.png")

app = FastAPI(
    title="Storage Service",
    docs_url=None,
    openapi_url="/openapi.json",
)


@app.get("/docs", include_in_schema=False)
async def swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="openapi.json",
        title=f"{app.title} - Swagger UI",
    )

DEFAULT_IMAGE_TYPE = "presence"
SUPPORTED_IMAGE_TYPES = {
    "presence",
    "status_code",
    "text_length",
    "timestamp_delta",
    "screenshot",
    "latitude_longitude",
}
IMAGE_TYPE_ALIASES = {
    "status_code": "status_code",
    "status code": "status_code",
    "text_length": "text_length",
    "text length": "text_length",
    "timestamp_delta": "timestamp_delta",
    "delta time": "timestamp_delta",
    "delta_time": "timestamp_delta",
    "screenshots": "screenshot",
    "screenshot": "screenshot",
    "latitude_longitude": "latitude_longitude",
    "geo": "latitude_longitude",
}


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
            _png_chunk(b"IDAT", zlib.compress(raw, level=3)),
            _png_chunk(b"IEND", b""),
        ]
    )


def _normalize_image_type(image_type: str | None) -> str:
    raw = str(image_type or "").strip().lower().replace("-", "_")
    if not raw:
        return DEFAULT_IMAGE_TYPE
    raw = raw.replace("__", "_")
    if raw in SUPPORTED_IMAGE_TYPES:
        return raw
    return IMAGE_TYPE_ALIASES.get(raw, DEFAULT_IMAGE_TYPE)


def _parse_float(value) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _scale_to_gray(value: float | None, min_value: float, max_value: float) -> int:
    if value is None:
        return 0
    if not math.isfinite(min_value) or not math.isfinite(max_value) or max_value <= min_value:
        return 180
    normalized = (value - min_value) / (max_value - min_value)
    return max(0, min(255, int(round(normalized * 255))))


def _rasterize_values(
    image_rows: list[dict],
    width: int,
    height: int,
    image_type: str,
) -> list[bytearray]:
    rows = [bytearray(width) for _ in range(height)]
    text_lengths = []
    delta_values = []
    prev_timestamp = None

    for row in image_rows:
        row["_text_length"] = _parse_float(row.get("text_length"))
        if row["_text_length"] is not None:
            text_lengths.append(row["_text_length"])
        timestamp = _parse_float(row.get("timestamp"))
        if timestamp is not None and timestamp < 1e12:
            timestamp *= 1000
        delta_value = None
        if timestamp is not None and prev_timestamp is not None:
            delta_value = max(0.0, timestamp - prev_timestamp)
            delta_values.append(delta_value)
        row["_timestamp"] = timestamp
        row["_delta_ms"] = delta_value
        if timestamp is not None:
            prev_timestamp = timestamp

    text_min = min(text_lengths) if text_lengths else 0.0
    text_max = max(text_lengths) if text_lengths else 1.0
    delta_min = min(delta_values) if delta_values else 0.0
    delta_max = max(delta_values) if delta_values else 1.0

    geo_values: list[float] = []
    for row in image_rows:
        la = _parse_float(row.get("latitude"))
        lo = _parse_float(row.get("longitude"))
        if la is None and lo is None:
            row["_geo_metric"] = None
        else:
            g = abs(la or 0.0) + abs(lo or 0.0)
            row["_geo_metric"] = g
            geo_values.append(g)
    geo_min = min(geo_values) if geo_values else 0.0
    geo_max = max(geo_values) if geo_values else 1.0

    for row in image_rows:
        step_id = row["number"]
        x = step_id % width
        y = step_id // width
        if y >= height:
            continue

        gray = 0
        if image_type == "presence":
            gray = 255
        elif image_type == "status_code":
            status_code = int(_parse_float(row.get("status_code")) or 0)
            if 400 <= status_code < 500:
                gray = 255
            elif 500 <= status_code < 600:
                gray = 208
            elif 300 <= status_code < 400:
                gray = 144
            elif 200 <= status_code < 300:
                gray = 96
            elif 100 <= status_code < 200:
                gray = 64
            else:
                gray = 32
        elif image_type == "text_length":
            gray = _scale_to_gray(row.get("_text_length"), text_min, text_max)
        elif image_type == "timestamp_delta":
            delta_value = row.get("_delta_ms")
            if delta_value is None:
                gray = 0
            elif delta_max <= delta_min:
                gray = 192
            else:
                normalized = (delta_value - delta_min) / (delta_max - delta_min)
                normalized = max(0.0, min(1.0, normalized))
                normalized = math.pow(normalized, 0.75)
                gray = max(0, min(255, int(round(235 * (1 - normalized)))))
        elif image_type == "screenshot":
            if "has_screenshot" in row:
                gray = 255 if int(row.get("has_screenshot") or 0) else 0
            else:
                gray = 255 if str(row.get("screenshot_url") or "").strip() else 0
        elif image_type == "latitude_longitude":
            gm = row.get("_geo_metric")
            gray = 0 if gm is None else _scale_to_gray(gm, geo_min, geo_max)

        rows[y][x] = gray
    return rows


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


@app.get("/stats")
async def stats():
    return await db_manager.get_stats()


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
async def get_latest(
    limit: int = 3000,
    fields: str | None = None,
    include_total: bool = False,
):
    safe_limit = max(1, min(int(limit), 20000))
    return await db_manager.get_latest(
        limit=safe_limit,
        fields=fields,
        include_total=include_total,
    )


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


# In-memory PNG cache: key (image_type, requested_width) -> entry
_IMG_CACHE_TTL_SEC = float(os.getenv("EXPORT_IMG_CACHE_TTL_SEC", "120"))
_img_cache: dict[tuple[str, int], dict] = {}
_img_cache_locks: dict[tuple[str, int], asyncio.Lock] = {}
_img_cache_meta_lock = asyncio.Lock()


async def _img_lock_for(key: tuple[str, int]) -> asyncio.Lock:
    async with _img_cache_meta_lock:
        lock = _img_cache_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _img_cache_locks[key] = lock
        return lock


def _img_cache_valid(entry: dict, max_step_id: int) -> bool:
    """TTL-fresh cache is a hit even if max_step_id advanced (avoids rebuild storm)."""
    if not entry or not entry.get("png_bytes"):
        return False
    built_at = entry.get("built_at")
    if built_at is None:
        return False
    if (time.monotonic() - built_at) >= _IMG_CACHE_TTL_SEC:
        return False
    # Immediate hit when nothing new; otherwise still serve within TTL.
    return True


def _gray_for_row(row: dict, image_type: str, *, text_min, text_max, delta_min, delta_max, geo_min, geo_max) -> int:
    if image_type == "presence":
        return 255
    if image_type == "status_code":
        status_code = int(_parse_float(row.get("status_code")) or 0)
        if 400 <= status_code < 500:
            return 255
        if 500 <= status_code < 600:
            return 208
        if 300 <= status_code < 400:
            return 144
        if 200 <= status_code < 300:
            return 96
        if 100 <= status_code < 200:
            return 64
        return 32
    if image_type == "text_length":
        return _scale_to_gray(row.get("_text_length"), text_min, text_max)
    if image_type == "timestamp_delta":
        delta_value = row.get("_delta_ms")
        if delta_value is None:
            return 0
        if delta_max <= delta_min:
            return 192
        normalized = (delta_value - delta_min) / (delta_max - delta_min)
        normalized = max(0.0, min(1.0, normalized))
        normalized = math.pow(normalized, 0.75)
        return max(0, min(255, int(round(235 * (1 - normalized)))))
    if image_type == "screenshot":
        if "has_screenshot" in row:
            return 255 if int(row.get("has_screenshot") or 0) else 0
        return 255 if str(row.get("screenshot_url") or "").strip() else 0
    if image_type == "latitude_longitude":
        gm = row.get("_geo_metric")
        return 0 if gm is None else _scale_to_gray(gm, geo_min, geo_max)
    return 0


async def _build_export_img(image_type: str, width: int, max_step_id: int) -> bytes:
    """Stream batches from DB and paint grayscale PNG without loading all rows."""
    if max_step_id is None:
        raise HTTPException(status_code=404, detail="No step ids available")
    img_width, img_height = _choose_presence_dimensions(max_step_id, width)
    canvas = [bytearray(img_width) for _ in range(img_height)]

    needs_stats = image_type in ("text_length", "timestamp_delta", "latitude_longitude")
    text_min = 0.0
    text_max = 1.0
    delta_min = 0.0
    delta_max = 1.0
    geo_min = 0.0
    geo_max = 1.0
    saw_any = False

    if needs_stats:
        text_lengths: list[float] = []
        delta_values: list[float] = []
        geo_values: list[float] = []
        prev_timestamp = None
        async for batch in db_manager.iter_image_row_batches(image_type):
            saw_any = True
            for row in batch:
                if image_type == "text_length":
                    tl = _parse_float(row.get("text_length"))
                    if tl is not None:
                        text_lengths.append(tl)
                elif image_type == "timestamp_delta":
                    timestamp = _parse_float(row.get("timestamp"))
                    if timestamp is not None and timestamp < 1e12:
                        timestamp *= 1000
                    if timestamp is not None and prev_timestamp is not None:
                        delta_values.append(max(0.0, timestamp - prev_timestamp))
                    if timestamp is not None:
                        prev_timestamp = timestamp
                elif image_type == "latitude_longitude":
                    la = _parse_float(row.get("latitude"))
                    lo = _parse_float(row.get("longitude"))
                    if la is not None or lo is not None:
                        geo_values.append(abs(la or 0.0) + abs(lo or 0.0))
        if text_lengths:
            text_min, text_max = min(text_lengths), max(text_lengths)
        if delta_values:
            delta_min, delta_max = min(delta_values), max(delta_values)
        if geo_values:
            geo_min, geo_max = min(geo_values), max(geo_values)

    prev_timestamp = None
    async for batch in db_manager.iter_image_row_batches(image_type):
        saw_any = True
        for row in batch:
            if image_type == "text_length":
                row["_text_length"] = _parse_float(row.get("text_length"))
            elif image_type == "timestamp_delta":
                timestamp = _parse_float(row.get("timestamp"))
                if timestamp is not None and timestamp < 1e12:
                    timestamp *= 1000
                delta_value = None
                if timestamp is not None and prev_timestamp is not None:
                    delta_value = max(0.0, timestamp - prev_timestamp)
                row["_delta_ms"] = delta_value
                if timestamp is not None:
                    prev_timestamp = timestamp
            elif image_type == "latitude_longitude":
                la = _parse_float(row.get("latitude"))
                lo = _parse_float(row.get("longitude"))
                row["_geo_metric"] = None if (la is None and lo is None) else abs(la or 0.0) + abs(lo or 0.0)

            step_id = row["number"]
            x = step_id % img_width
            y = step_id // img_width
            if y >= img_height:
                continue
            canvas[y][x] = _gray_for_row(
                row,
                image_type,
                text_min=text_min,
                text_max=text_max,
                delta_min=delta_min,
                delta_max=delta_max,
                geo_min=geo_min,
                geo_max=geo_max,
            )

    if not saw_any:
        raise HTTPException(status_code=404, detail="No step ids available")
    return _build_grayscale_png(canvas, img_width, img_height)


@app.get("/export/img")
async def export_img(width: int = 0, type: str = DEFAULT_IMAGE_TYPE):
    image_type = _normalize_image_type(type)
    requested_width = int(width) if width else 0
    cache_key = (image_type, requested_width)

    max_step_id = await db_manager.get_max_step_number()
    if max_step_id is None:
        raise HTTPException(status_code=404, detail="No step ids available")

    cached = _img_cache.get(cache_key)
    if cached and _img_cache_valid(cached, max_step_id):
        return StreamingResponse(
            io.BytesIO(cached["png_bytes"]),
            media_type="image/png",
            headers={
                "Content-Disposition": f'inline; filename="presence_{image_type}.png"',
                "X-Export-Img-Cache": "hit",
            },
        )

    lock = await _img_lock_for(cache_key)
    async with lock:
        # Re-check after acquiring single-flight lock
        max_step_id = await db_manager.get_max_step_number()
        if max_step_id is None:
            raise HTTPException(status_code=404, detail="No step ids available")
        cached = _img_cache.get(cache_key)
        if cached and _img_cache_valid(cached, max_step_id):
            return StreamingResponse(
                io.BytesIO(cached["png_bytes"]),
                media_type="image/png",
                headers={
                    "Content-Disposition": f'inline; filename="presence_{image_type}.png"',
                    "X-Export-Img-Cache": "hit",
                },
            )

        try:
            t0 = time.monotonic()
            png_bytes = await _build_export_img(image_type, requested_width, max_step_id)
            logger.info(
                "export/img built type=%s width=%s max_step_id=%s bytes=%s in %.2fs",
                image_type,
                requested_width,
                max_step_id,
                len(png_bytes),
                time.monotonic() - t0,
            )
        except HTTPException:
            raise
        except Exception:
            logger.exception("export/img build failed type=%s width=%s", image_type, requested_width)
            raise HTTPException(status_code=500, detail="Failed to build steps image")
        _img_cache[cache_key] = {
            "png_bytes": png_bytes,
            "max_step_id": max_step_id,
            "built_at": time.monotonic(),
        }

    return StreamingResponse(
        io.BytesIO(png_bytes),
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="presence_{image_type}.png"',
            "X-Export-Img-Cache": "miss",
        },
    )


@app.get("/backfill/image")
async def backfill_image():
    try:
        if not os.path.isfile(BACKFILL_IMAGE_PATH) or os.path.getsize(BACKFILL_IMAGE_PATH) == 0:
            raise HTTPException(status_code=404, detail="Backfill image not found")
    except OSError:
        raise HTTPException(status_code=404, detail="Backfill image not found")

    return FileResponse(
        BACKFILL_IMAGE_PATH,
        media_type="image/png",
        filename="backfill_presence.png",
        headers={"Cache-Control": "no-cache"},
    )
