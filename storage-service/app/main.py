from fastapi import FastAPI, Request, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from app.api.db import metadata, database, engine
from app.api import db_manager
import asyncio
import logging
import os

logger = logging.getLogger("storage_service")
logging.basicConfig(level=logging.INFO)

app = FastAPI()


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


@app.get("/get/step/{number}")
async def get_step(number: str):
    step = await db_manager.get_step_by_number(number)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    return step


@app.get("/get/latest")
async def get_latest():
    return await db_manager.get_latest()
