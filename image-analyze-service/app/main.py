import io
import os
from typing import List

import numpy as np
import requests
from fastapi import FastAPI, HTTPException
from PIL import Image
from pydantic import BaseModel, Field
from sklearn.cluster import KMeans


DEFAULT_N_COLORS = int(os.getenv("IMAGE_ANALYZE_DEFAULT_N_COLORS", "7"))
MAX_PIXELS = int(os.getenv("IMAGE_ANALYZE_MAX_PIXELS", "200000"))
REQUEST_TIMEOUT = float(os.getenv("IMAGE_ANALYZE_REQUEST_TIMEOUT", "30"))

app = FastAPI(
    title="Image Analyze Service",
    version="0.1.0",
    openapi_url="/api/v1/image-analyze/openapi.json",
    docs_url="/api/v1/image-analyze/docs",
)


class AnalyzeRequest(BaseModel):
    image_url: str
    n_colors: int = Field(default=DEFAULT_N_COLORS, ge=1, le=16)


class AnalyzeResponse(BaseModel):
    palette: List[str]
    image_url: str


def _resize_pixels(pixels: np.ndarray) -> np.ndarray:
    if len(pixels) <= MAX_PIXELS:
        return pixels
    step = max(1, len(pixels) // MAX_PIXELS)
    return pixels[::step]


def _rgb_to_hex(rgb: np.ndarray) -> str:
    r, g, b = [int(np.clip(round(float(channel)), 0, 255)) for channel in rgb[:3]]
    return f"#{r:02X}{g:02X}{b:02X}"


def _extract_palette(image_bytes: bytes, n_colors: int) -> List[str]:
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image payload: {exc}") from exc

    pixels = np.asarray(image).reshape(-1, 3)
    pixels = _resize_pixels(pixels)
    if len(pixels) == 0:
        raise HTTPException(status_code=400, detail="Image has no pixels")

    cluster_count = min(n_colors, len(pixels))
    model = KMeans(n_clusters=cluster_count, random_state=0, n_init=10)
    labels = model.fit_predict(pixels)
    counts = np.bincount(labels, minlength=cluster_count)
    sorted_indices = np.argsort(counts)[::-1]
    palette = [_rgb_to_hex(model.cluster_centers_[idx]) for idx in sorted_indices]
    return palette


@app.get("/")
def root():
    return {"service": "image-analyze-service", "status": "ok"}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/api/v1/image-analyze/analyze/", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest):
    try:
        response = requests.get(payload.image_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Unable to fetch image: {exc}") from exc

    palette = _extract_palette(response.content, payload.n_colors)
    return AnalyzeResponse(palette=palette, image_url=payload.image_url)
