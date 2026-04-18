"""HTTP API for mood + palette."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.mood_engine import get_mood_and_palette, load_models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        load_models()
    except Exception as exc:
        logger.exception("Warmup load_models failed: %s", exc)
    yield


app = FastAPI(title="mood-service", lifespan=lifespan)


class MoodSnapshotRequest(BaseModel):
    text: str = ""
    semantic: Optional[Dict[str, Any]] = Field(default=None)


@app.get("/health")
def health():
    return {"ok": True, "service": "mood-service"}


@app.post("/api/v1/mood/snapshot/")
def mood_snapshot(req: MoodSnapshotRequest):
    try:
        return get_mood_and_palette(req.text or "", req.semantic)
    except Exception as exc:
        logger.exception("mood snapshot failed: %s", exc)
        return {
            "timestamp": "",
            "dominant_mood": "error",
            "mood_scores_nn": {},
            "rule_scores": {},
            "full_description": str(exc)[:200],
            "palette": [{"hex": "#333333", "name": "error", "mood": "", "emotion": ""}],
            "palette_description": "error",
            "update_interval_ok": False,
            "error": str(exc)[:500],
        }
