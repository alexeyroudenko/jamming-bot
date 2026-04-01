import asyncio
import json
import logging
import math
import os
import struct
import urllib.error
import urllib.request
import zlib
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, Response


logger = logging.getLogger("steps_service")
logging.basicConfig(level=logging.INFO)

DEFAULT_STORAGE_IDS_URL = os.getenv(
    "STEPS_STORAGE_IDS_URL",
    "http://storage_service:7781/get/ids",
)
DEFAULT_REFRESH_SECONDS = int(os.getenv("STEPS_REFRESH_SECONDS", "60"))
DEFAULT_OUTPUT_DIR = Path(
    os.getenv("STEPS_OUTPUT_DIR", "/tmp/steps-service")
).resolve()
DEFAULT_WIDTH = int(os.getenv("STEPS_CANVAS_WIDTH", "0"))


def fetch_json(url: str):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "steps-service/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def extract_step_ids(payload) -> list[int]:
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            raw_ids = payload["data"]
        elif isinstance(payload.get("ids"), list):
            raw_ids = payload["ids"]
        else:
            raise ValueError("Unsupported JSON payload: expected list in data or ids")
    elif isinstance(payload, list):
        raw_ids = payload
    else:
        raise ValueError("Unsupported JSON payload type")

    step_ids = sorted(
        {
            int(float(value))
            for value in raw_ids
            if value is not None and str(value).strip() != ""
        }
    )
    if not step_ids:
        raise ValueError("No step ids returned by API")
    return step_ids


def choose_dimensions(step_count: int, requested_width: int) -> tuple[int, int]:
    width = requested_width if requested_width > 0 else max(1, math.ceil(math.sqrt(step_count)))
    height = max(1, math.ceil(step_count / width))
    return width, height


def rasterize_presence(step_ids: list[int], width: int, height: int) -> list[bytearray]:
    rows = [bytearray(width) for _ in range(height)]
    for index, _step_id in enumerate(step_ids):
        x = index % width
        y = index // width
        rows[y][x] = 255
    return rows


def png_chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack("!I", len(data))
        + tag
        + data
        + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def encode_grayscale_png(rows: list[bytearray], width: int, height: int) -> bytes:
    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    header = struct.pack("!2I5B", width, height, 8, 0, 0, 0, 0)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            png_chunk(b"IHDR", header),
            png_chunk(b"IDAT", zlib.compress(raw, level=9)),
            png_chunk(b"IEND", b""),
        ]
    )


@dataclass
class PresenceState:
    width: int = 1
    height: int = 1
    step_ids: list[int] = field(default_factory=list)
    step_count: int = 0
    min_step_id: int | None = None
    max_step_id: int | None = None
    png_bytes: bytes = b""
    updated_at: str | None = None
    error: str | None = None


state = PresenceState()
state_lock = asyncio.Lock()
refresh_task: asyncio.Task | None = None


def render_html() -> str:
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Steps Presence</title>
    <style>
      :root {
        color-scheme: dark;
      }
      html, body {
        width: 100%;
        height: 100%;
        margin: 0;
        overflow: hidden;
        background: #000;
        font-family: sans-serif;
      }
      #stage {
        position: fixed;
        inset: 0;
      }
      #presence {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        object-fit: fill;
        image-rendering: pixelated;
        user-select: none;
        -webkit-user-drag: none;
      }
      #overlay {
        position: absolute;
        inset: 0;
        cursor: crosshair;
      }
      #tooltip {
        position: fixed;
        display: none;
        pointer-events: none;
        transform: translate(12px, 12px);
        padding: 6px 10px;
        border-radius: 8px;
        background: rgba(0, 0, 0, 0.82);
        color: #fff;
        font-size: 14px;
        line-height: 1.2;
        white-space: nowrap;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
      }
      #status {
        position: fixed;
        left: 12px;
        bottom: 12px;
        padding: 6px 10px;
        border-radius: 8px;
        background: rgba(0, 0, 0, 0.72);
        color: rgba(255, 255, 255, 0.85);
        font-size: 12px;
      }
    </style>
  </head>
  <body>
    <div id="stage">
      <img id="presence" alt="steps presence" src="./presence_raw.png" />
      <div id="overlay"></div>
    </div>
    <div id="tooltip"></div>
    <div id="status">Loading...</div>
    <script>
      const image = document.getElementById("presence");
      const overlay = document.getElementById("overlay");
      const tooltip = document.getElementById("tooltip");
      const status = document.getElementById("status");
      const baseUrl = new URL(
        window.location.pathname.endsWith("/") ? window.location.href : window.location.href + "/"
      );

      let requestId = 0;

      function setTooltip(text, x, y) {
        tooltip.style.display = "block";
        tooltip.textContent = text;
        tooltip.style.left = x + "px";
        tooltip.style.top = y + "px";
      }

      function hideTooltip() {
        tooltip.style.display = "none";
      }

      async function refreshImage() {
        const stamp = Date.now();
        image.src = new URL(`presence_raw.png?v=${stamp}`, baseUrl).toString();
        try {
          const response = await fetch(new URL("healthz", baseUrl), { cache: "no-store" });
          const payload = await response.json();
          status.textContent = payload.updated_at
            ? `steps: ${payload.step_count}, updated: ${payload.updated_at}`
            : "Waiting for first render...";
        } catch (error) {
          status.textContent = "Status unavailable";
        }
      }

      async function handlePointer(event) {
        if (!image.naturalWidth || !image.naturalHeight) {
          hideTooltip();
          return;
        }

        const rect = overlay.getBoundingClientRect();
        const normalizedX = (event.clientX - rect.left) / rect.width;
        const normalizedY = (event.clientY - rect.top) / rect.height;
        const x = Math.max(0, Math.min(image.naturalWidth - 1, Math.floor(normalizedX * image.naturalWidth)));
        const y = Math.max(0, Math.min(image.naturalHeight - 1, Math.floor(normalizedY * image.naturalHeight)));
        const currentRequestId = ++requestId;

        try {
          const tooltipUrl = new URL(`api/tooltip?x=${x}&y=${y}`, baseUrl);
          const response = await fetch(tooltipUrl, { cache: "no-store" });
          if (currentRequestId !== requestId) {
            return;
          }
          const payload = await response.json();
          if (payload.step_id === null || payload.step_id === undefined) {
            hideTooltip();
            return;
          }
          setTooltip(`Step ${payload.step_id}`, event.clientX, event.clientY);
        } catch (error) {
          hideTooltip();
        }
      }

      overlay.addEventListener("mousemove", handlePointer);
      overlay.addEventListener("mouseleave", hideTooltip);

      refreshImage();
      setInterval(refreshImage, 60000);
    </script>
  </body>
</html>
"""


def write_snapshot(output_dir: Path, png_bytes: bytes, metadata: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "presence_raw.png").write_bytes(png_bytes)
    (output_dir / "presence_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


async def refresh_presence() -> None:
    payload = await asyncio.to_thread(fetch_json, DEFAULT_STORAGE_IDS_URL)
    step_ids = extract_step_ids(payload)
    max_step_id = step_ids[-1]
    width, height = choose_dimensions(len(step_ids), DEFAULT_WIDTH)
    rows = rasterize_presence(step_ids, width, height)
    png_bytes = encode_grayscale_png(rows, width, height)
    metadata = {
        "storage_ids_url": DEFAULT_STORAGE_IDS_URL,
        "step_count": len(step_ids),
        "min_step_id": step_ids[0],
        "max_step_id": max_step_id,
        "layout": "compact-grid",
        "width": width,
        "height": height,
    }
    await asyncio.to_thread(write_snapshot, DEFAULT_OUTPUT_DIR, png_bytes, metadata)

    async with state_lock:
        state.width = width
        state.height = height
        state.step_ids = step_ids
        state.step_count = len(step_ids)
        state.min_step_id = step_ids[0]
        state.max_step_id = max_step_id
        state.png_bytes = png_bytes
        state.updated_at = datetime.now(timezone.utc).isoformat()
        state.error = None


async def refresh_loop() -> None:
    while True:
        try:
            await refresh_presence()
            logger.info("Presence updated: %s steps", state.step_count)
        except urllib.error.URLError as exc:
            message = f"Failed to fetch {DEFAULT_STORAGE_IDS_URL}: {exc}"
            logger.exception(message)
            async with state_lock:
                state.error = message
        except (ValueError, json.JSONDecodeError) as exc:
            message = f"Invalid API response from {DEFAULT_STORAGE_IDS_URL}: {exc}"
            logger.exception(message)
            async with state_lock:
                state.error = message
        except Exception as exc:
            message = f"Unexpected refresh error: {exc}"
            logger.exception(message)
            async with state_lock:
                state.error = message
        await asyncio.sleep(max(1, DEFAULT_REFRESH_SECONDS))


@asynccontextmanager
async def lifespan(_: FastAPI):
    global refresh_task
    refresh_task = asyncio.create_task(refresh_loop())
    try:
        yield
    finally:
        if refresh_task is not None:
            refresh_task.cancel()
            with suppress(asyncio.CancelledError):
                await refresh_task


app = FastAPI(
    title="Steps Service",
    version="0.1.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    lifespan=lifespan,
)


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    return HTMLResponse(render_html())


@app.get("/healthz")
async def healthz():
    async with state_lock:
        return {
            "status": "ok" if state.png_bytes else "warming_up",
            "step_count": state.step_count,
            "width": state.width,
            "height": state.height,
            "updated_at": state.updated_at,
            "error": state.error,
        }


@app.get("/presence_raw.png")
async def presence_raw_png() -> Response:
    async with state_lock:
        if not state.png_bytes:
            raise HTTPException(status_code=503, detail="Presence image not ready yet")
        return Response(content=state.png_bytes, media_type="image/png")


@app.get("/api/tooltip")
async def tooltip(
    x: int = Query(..., ge=0),
    y: int = Query(..., ge=0),
):
    async with state_lock:
        if not state.png_bytes:
            raise HTTPException(status_code=503, detail="Presence image not ready yet")
        if x >= state.width or y >= state.height:
            return {"step_id": None}
        index = y * state.width + x
        if index >= len(state.step_ids):
            return {"step_id": None}
        return {"step_id": state.step_ids[index]}
