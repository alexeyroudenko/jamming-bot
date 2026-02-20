from fastapi import FastAPI
from app.api.tags import tags
from app.api.db import metadata, database, engine
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import os

import os
import sentry_sdk
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration

SENTRY_DSN = os.getenv('SENTRY_DSN', '')
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            StarletteIntegration(
                transaction_style="endpoint",
                failed_request_status_codes={403, *range(500, 599)},
                http_methods_to_capture=("GET",),
            ),
            FastApiIntegration(
                transaction_style="endpoint",
                failed_request_status_codes={403, *range(500, 599)},
                http_methods_to_capture=("GET",),
            ),
        ],
        enable_logs=True,
        traces_sample_rate=1.0,
    )


logger = logging.getLogger("tags_service")
logging.basicConfig(level=logging.INFO)

app = FastAPI(openapi_url="/api/v1/tags/openapi.json", docs_url="/api/v1/tags/docs")

origins = [
    "http://localhost:3000",
    "https://example.com",
    "http://192.168.31.18:3000",
    "http://192.168.31.18:8003",
    "http://192.168.31.18:5000",
    "http://192.168.0.104:3000",
    "http://192.168.0.104:8003",
    "http://192.168.0.104:5000",
    "http://192.168.0.104:3000",
    "http://192.168.0.104:8003",
    "http://bots.local:3000",
    "http://0.0.0.0:3000",
    "http://bots.local:8003",
    "http://bots.local:5000",
    "http://10.8.0.11:3000",
    "http://jamming-bot.arthew0.online:3000",
    "https://jamming-bot.arthew0.online",
    "http://jamming-bot.arthew0.online"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def _init_db_with_retry():
    """Create tables with retry so the container does not exit if DB is not yet resolvable."""
    max_attempts = int(os.getenv("DB_INIT_MAX_ATTEMPTS", "15"))
    delay = float(os.getenv("DB_INIT_DELAY_SECONDS", "2"))
    for attempt in range(1, max_attempts + 1):
        try:
            metadata.create_all(engine)
            logger.info("Database initialization successful on attempt %s", attempt)
            return
        except Exception as e:  # broad to handle DNS / connection issues
            if attempt == max_attempts:
                logger.error("Database initialization failed after %s attempts: %s", attempt, e)
                raise
            logger.warning("DB not ready (attempt %s/%s): %s; retrying in %.1fs", attempt, max_attempts, e, delay)
            await asyncio.sleep(delay)

@app.on_event("startup")
async def startup():
    await _init_db_with_retry()
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


app.include_router(tags, prefix='/api/v1/tags', tags=['tags'])
# app.include_router(tags, prefix='/api/v1/tags/group', tags=['tags'])

