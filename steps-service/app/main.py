import asyncio
import csv
import json
import logging
import os
import struct
import urllib.error
import urllib.parse
import urllib.request
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response


logger = logging.getLogger("steps_service")
logging.basicConfig(level=logging.INFO)

DEFAULT_IMAGE_URL = os.getenv(
    "STEPS_IMAGE_URL",
    "http://localhost:5000/api/storage_img/",
)
DEFAULT_LATEST_URL = os.getenv(
    "STEPS_LATEST_URL",
    "http://localhost:5000/api/storage_latest/",
)
DEFAULT_STEPS_CSV_URL = os.getenv(
    "STEPS_CSV_URL",
    "http://storage_service:7781/export/csv",
)
DEFAULT_REFRESH_SECONDS = int(os.getenv("STEPS_REFRESH_SECONDS", "60"))
DEFAULT_OUTPUT_DIR = Path(
    os.getenv("STEPS_OUTPUT_DIR", "/tmp/steps-service")
).resolve()
DEFAULT_IMAGE_TYPE = "status_code"
SUPPORTED_IMAGE_TYPES = (
    "status_code",
    "text_length",
    "timestamp_delta",
    "screenshot",
    "latitude_longitude",
)
IMAGE_TYPE_ALIASES = {
    "status_code": "status_code",
    "status code": "status_code",
    "text_length": "text_length",
    "text length": "text_length",
    "timestamp_delta": "timestamp_delta",
    "delta_time": "timestamp_delta",
    "delta time": "timestamp_delta",
    "screenshot": "screenshot",
    "screenshots": "screenshot",
    "latitude_longitude": "latitude_longitude",
    "geo": "latitude_longitude",
}


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "image/png,image/*;q=0.9,*/*;q=0.1",
            "User-Agent": "steps-service/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


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


def fetch_csv_rows(url: str) -> list[dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/csv,*/*;q=0.1",
            "User-Agent": "steps-service/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        text = response.read().decode("utf-8", errors="replace")
    return list(csv.DictReader(text.splitlines()))


def parse_png_dimensions(png_bytes: bytes) -> tuple[int, int]:
    if len(png_bytes) < 24 or png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Invalid PNG payload")
    return struct.unpack("!II", png_bytes[16:24])


def normalize_image_type(raw_type: str | None) -> str:
    key = str(raw_type or "").strip().lower().replace("-", "_")
    if not key:
        return DEFAULT_IMAGE_TYPE
    if key in SUPPORTED_IMAGE_TYPES:
        return key
    return IMAGE_TYPE_ALIASES.get(key, DEFAULT_IMAGE_TYPE)


def image_snapshot_name(image_type: str) -> str:
    return f"steps_{image_type}.png"


@dataclass
class ImageSnapshot:
    width: int = 1
    height: int = 1
    png_bytes: bytes = b""


@dataclass
class PresenceState:
    snapshots: dict[str, ImageSnapshot] | None = None
    steps_payload: dict | None = None
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
    <link rel="stylesheet" href="/flask_static/style.css" />
    <style>
      :root {
        color-scheme: dark;
        --steps-bg: var(--jb-surface-glass);
        --steps-panel: var(--jb-surface-raised);
        --steps-border: var(--jb-color-border);
        --steps-text: var(--jb-color-text);
        --steps-muted: var(--jb-color-text-muted);
        --steps-accent: var(--jb-color-accent);
      }
      html, body {
        width: 100%;
        height: 100%;
        margin: 0;
        overflow: hidden;
        background: var(--jb-color-bg-page);
        font-family: var(--jb-font-sans);
      }
      .steps-nav {
        position: fixed;
        top: 12px;
        left: 12px;
        right: 12px;
        z-index: 20;
        display: flex;
        justify-content: space-between;
        gap: 12px;
        padding: 8px 12px;
        border-radius: 12px;
        background: var(--steps-bg);
        border: 1px solid var(--steps-border);
        backdrop-filter: blur(10px);
      }
      .steps-nav,
      .steps-nav a {
        color: var(--steps-muted);
        font-size: 12px;
        text-decoration: none;
      }
      .steps-nav-title {
        color: var(--steps-text);
        font-weight: 600;
        margin-right: 12px;
      }
      .steps-toolbar {
        position: fixed;
        top: 64px;
        left: 12px;
        z-index: 20;
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
        max-width: calc(100vw - 24px);
        padding: 10px 12px;
        border-radius: 12px;
        background: var(--steps-bg);
        border: 1px solid var(--steps-border);
        backdrop-filter: blur(10px);
      }
      .steps-btn,
      .steps-mode-label {
        appearance: none;
        border: 1px solid var(--steps-border);
        border-radius: 999px;
        background: rgba(24, 24, 27, 0.84);
        color: var(--steps-text);
        padding: 7px 12px;
        font-size: 12px;
        cursor: pointer;
      }
      .steps-btn[aria-pressed="true"] {
        border-color: rgba(34, 211, 238, 0.45);
        box-shadow: 0 0 0 1px rgba(34, 211, 238, 0.22) inset;
        color: var(--steps-accent);
      }
      .steps-mode-group {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
      }
      .steps-mode-label {
        display: inline-flex;
        align-items: center;
        gap: 6px;
      }
      .steps-mode-label input {
        accent-color: var(--steps-accent);
      }
      .steps-status {
        color: var(--steps-muted);
        font-size: 11px;
        font-family: ui-monospace, monospace;
      }
      #stage {
        position: fixed;
        inset: 0;
        overflow: hidden;
        background: var(--jb-color-bg-page);
      }
      #stage.steps-stage-fit-scale,
      #stage.steps-stage-fit-noscale {
        background: #09090b;
      }
      #presence {
        position: absolute;
        image-rendering: pixelated;
        user-select: none;
        -webkit-user-drag: none;
      }
      #presence.steps-presence-fit-scale {
        inset: 0;
        width: 100%;
        height: 100%;
        transform: none;
        left: auto;
        top: auto;
        object-fit: cover;
      }
      #presence.steps-presence-fit-noscale {
        inset: auto;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
        object-fit: none;
        max-width: none;
        max-height: none;
      }
      #overlay {
        position: absolute;
        inset: 0;
        cursor: crosshair;
      }
      #tooltip {
        position: fixed;
        z-index: 25;
        display: block;
        pointer-events: none;
        opacity: 0;
        min-width: 240px;
        max-width: min(420px, calc(100vw - 24px));
        padding: 10px 12px;
        border-radius: 10px;
        border: 1px solid var(--steps-border);
        background: var(--steps-panel);
        color: var(--steps-text);
        box-shadow: 0 12px 38px rgba(0, 0, 0, 0.42);
        font-size: 12px;
        line-height: 1.45;
        backdrop-filter: blur(8px);
        transition: opacity 0.14s ease, left 0.2s ease, top 0.2s ease;
      }
      #tooltip.visible {
        opacity: 1;
      }
      .steps-tooltip-row {
        margin-top: 4px;
      }
      .steps-tooltip-label {
        color: var(--steps-muted);
        margin-right: 6px;
      }
      .steps-tooltip-image {
        display: block;
        width: 220px;
        max-width: 100%;
        margin-top: 10px;
        border-radius: 6px;
        border: 1px solid var(--steps-border);
        background: #000;
        object-fit: cover;
      }
      .steps-auto-cursor {
        position: fixed;
        width: 16px;
        height: 16px;
        border: 1px solid var(--steps-accent);
        border-radius: 999px;
        box-shadow: 0 0 0 1px rgba(9, 9, 11, 0.88), 0 0 22px rgba(34, 211, 238, 0.55);
        pointer-events: none;
        z-index: 24;
        opacity: 0;
        transform: translate(-50%, -50%);
        transition: opacity 0.18s ease;
      }
      .steps-auto-cursor.visible {
        opacity: 1;
      }
      .steps-auto-cursor::after {
        content: "";
        position: absolute;
        inset: 4px;
        border-radius: 999px;
        background: rgba(34, 211, 238, 0.8);
      }
      #pixel-source {
        display: none;
      }
      .steps-backfill-panel {
        position: fixed;
        top: 64px;
        right: 12px;
        z-index: 21;
        max-width: min(320px, calc(100vw - 24px));
        border-radius: 12px;
        border: 1px solid var(--steps-border);
        background: var(--steps-panel);
        backdrop-filter: blur(10px);
        font-size: 12px;
        color: var(--steps-text);
        box-shadow: 0 12px 38px rgba(0, 0, 0, 0.35);
      }
      .steps-backfill-panel > summary {
        list-style: none;
        cursor: pointer;
        padding: 10px 12px;
        font-weight: 600;
        color: var(--steps-muted);
        user-select: none;
      }
      .steps-backfill-panel > summary::-webkit-details-marker {
        display: none;
      }
      .steps-backfill-panel[open] > summary {
        color: var(--steps-accent);
        border-bottom: 1px solid var(--steps-border);
      }
      .steps-backfill-inner {
        padding: 10px 12px 12px;
      }
      .steps-backfill-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px 12px;
      }
      .steps-backfill-item {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }
      .steps-backfill-label {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--steps-muted);
      }
      .steps-backfill-value {
        font-family: ui-monospace, monospace;
        font-size: 11px;
        word-break: break-all;
      }
      .steps-backfill-value.is-running { color: #4ade80; }
      .steps-backfill-value.is-finished { color: var(--steps-muted); }
      .steps-backfill-value.is-failed { color: #f87171; }
      .steps-backfill-detail {
        margin-top: 10px;
        padding-top: 8px;
        border-top: 1px solid var(--steps-border);
        font-size: 11px;
        line-height: 1.4;
        color: var(--steps-muted);
        word-break: break-word;
      }
      .steps-presence-anchor {
        position: fixed;
        width: 10px;
        height: 10px;
        border-radius: 999px;
        background: #ff0000;
        box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.85), 0 0 12px rgba(255, 0, 0, 0.7);
        transform: translate(-50%, -50%);
        z-index: 26;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.2s ease, transform 0.45s ease;
      }
      .steps-presence-anchor.visible {
        opacity: 1;
      }
      .steps-presence-anchor.fading {
        opacity: 0;
        transform: translate(-50%, -50%) scale(0.82);
      }
    </style>
  </head>
  <body>
    <nav class="steps-nav" aria-label="Subpages">
      <div>
        <span class="steps-nav-title">Steps</span>
        <a href="/">← home</a>
        <a href="/path/map/">path map</a>
      </div>
    </nav>
    <div class="steps-toolbar">
      <button type="button" class="steps-btn" id="btn-auto" aria-pressed="false">Auto</button>
      <button type="button" class="steps-btn" id="btn-refresh">Refresh</button>
      <fieldset class="steps-mode-group">
        <legend style="display:none">Metric type</legend>
        <label class="steps-mode-label"><input type="radio" name="display-type" value="status_code">status code</label>
        <label class="steps-mode-label"><input type="radio" name="display-type" value="text_length">text length</label>
        <label class="steps-mode-label"><input type="radio" name="display-type" value="timestamp_delta">delta time</label>
        <label class="steps-mode-label"><input type="radio" name="display-type" value="screenshot">screenshots</label>
        <label class="steps-mode-label"><input type="radio" name="display-type" value="latitude_longitude">geo</label>
        <label class="steps-mode-label"><input type="radio" name="display-type" value="error">error</label>
      </fieldset>
      <fieldset class="steps-mode-group">
        <legend style="display:none">Image fit</legend>
        <label class="steps-mode-label"><input type="radio" name="image-fit" value="scale">scale</label>
        <label class="steps-mode-label"><input type="radio" name="image-fit" value="no-scale">no-scale</label>
      </fieldset>
      <span class="steps-status" id="status">Loading...</span>
    </div>
    <div id="stage">
      <img id="presence" alt="steps presence" src="./api/image" crossorigin="anonymous" />
      <div id="overlay"></div>
    </div>
    <canvas id="pixel-source"></canvas>
    <div id="tooltip"></div>
    <div id="presence-anchors" aria-hidden="true"></div>
    <div id="auto-cursor" class="steps-auto-cursor" aria-hidden="true"></div>
    <details id="steps-backfill" class="steps-backfill-panel" aria-live="polite">
      <summary>Backfill</summary>
      <div class="steps-backfill-inner">
        <div class="steps-backfill-meta steps-backfill-label" id="steps-bf-meta">—</div>
        <div class="steps-backfill-grid" style="margin-top:10px">
          <div class="steps-backfill-item">
            <span class="steps-backfill-label">State</span>
            <span id="steps-bf-state" class="steps-backfill-value">idle</span>
          </div>
          <div class="steps-backfill-item">
            <span class="steps-backfill-label">Step</span>
            <span id="steps-bf-step" class="steps-backfill-value">—</span>
          </div>
          <div class="steps-backfill-item">
            <span class="steps-backfill-label">Page</span>
            <span id="steps-bf-page" class="steps-backfill-value">0 / 0</span>
          </div>
          <div class="steps-backfill-item">
            <span class="steps-backfill-label">Processed</span>
            <span id="steps-bf-processed" class="steps-backfill-value">0</span>
          </div>
          <div class="steps-backfill-item">
            <span class="steps-backfill-label">Skipped</span>
            <span id="steps-bf-skipped" class="steps-backfill-value">0</span>
          </div>
          <div class="steps-backfill-item">
            <span class="steps-backfill-label">Sleep</span>
            <span id="steps-bf-sleep" class="steps-backfill-value">—</span>
          </div>
          <div class="steps-backfill-item">
            <span class="steps-backfill-label">Timeout</span>
            <span id="steps-bf-timeout" class="steps-backfill-value">—</span>
          </div>
          <div class="steps-backfill-item">
            <span class="steps-backfill-label">Delta sec</span>
            <span id="steps-bf-delta" class="steps-backfill-value">—</span>
          </div>
        </div>
        <div id="steps-bf-detail" class="steps-backfill-detail">No data yet</div>
      </div>
    </details>
    <script src="https://cdn.socket.io/4.7.5/socket.io.min.js" integrity="sha384-2huaZvOR9iDzHqslqwpR87isEmrfxqyWOF7hr7BY6KG0+hVKLoEXMPUJw3ynWuhO" crossorigin="anonymous"></script>
    <script>
      const TYPE_STORAGE_KEY = "steps-display-type";
      const FIT_STORAGE_KEY = "steps-image-fit";
      const DEFAULT_IMAGE_TYPE = "status_code";
      const TYPE_ALIASES = {
        status_code: "status_code",
        "status code": "status_code",
        text_length: "text_length",
        "text length": "text_length",
        timestamp_delta: "timestamp_delta",
        delta_time: "timestamp_delta",
        "delta time": "timestamp_delta",
        screenshot: "screenshot",
        screenshots: "screenshot"
      };
      const VALID_TYPES = new Set([
        "status_code",
        "text_length",
        "timestamp_delta",
        "screenshot",
        "latitude_longitude",
        "error"
      ]);
      const VALID_FITS = new Set(["scale", "no-scale"]);

      const image = document.getElementById("presence");
      const stageEl = document.getElementById("stage");
      const overlay = document.getElementById("overlay");
      const tooltip = document.getElementById("tooltip");
      const statusEl = document.getElementById("status");
      const pixelSource = document.getElementById("pixel-source");
      const pixelContext = pixelSource.getContext("2d", { willReadFrequently: true });
      const presenceAnchorsHost = document.getElementById("presence-anchors");
      const autoCursor = document.getElementById("auto-cursor");
      const autoBtn = document.getElementById("btn-auto");
      const refreshBtn = document.getElementById("btn-refresh");
      const typeInputs = Array.from(document.querySelectorAll('input[name="display-type"]'));
      const fitInputs = Array.from(document.querySelectorAll('input[name="image-fit"]'));
      const baseUrl = new URL(
        window.location.pathname.endsWith("/") ? window.location.href : window.location.href + "/"
      );

      let imageReady = false;
      let pendingPointerEvent = null;
      let animationFrameId = 0;
      let steps = [];
      let stepMap = new Map();
      const stepCache = new Map();
      const pendingStepRequests = new Map();
      let stepDetailTimer = null;
      const STEP_DETAIL_DELAY_MS = 100;
      const AUTO_ID_SPREAD_MULTIPLIER = 20;
      const AUTO_ID_FOCUS = 100000;
      let displayType = "status_code";
      let imageFitMode = "no-scale";
      let hoveredStepId = null;
      let latestStepNumber = -1;
      let autoMode = false;
      let autoTarget = null;
      let autoTimer = null;
      let autoAnimationFrame = null;
      let presenceDebounceTimer = null;
      let pendingPresenceStep = null;
      let pendingAnchorAfterImageLoad = null;
      let socketImageRefreshTimer = null;
      let lastSocketImageRefreshAt = 0;
      let tooltipPositionReady = false;
      const MAX_PRESENCE_ANCHORS = 100;
      const PRESENCE_ANCHOR_FADE_MS = 7000;
      const SOCKET_PRESENCE_DEBOUNCE_MS = 600;
      const SOCKET_IMAGE_REFRESH_MIN_INTERVAL_MS = 45000;
      const presenceAnchors = [];
      const autoState = { x: 0, y: 0, targetX: 0, targetY: 0, vx: 0, vy: 0 };

      function trimText(value) {
        return String(value == null ? "" : value).trim();
      }

      function parseStepNumber(value, fallback) {
        const n = parseInt(String(value == null ? "" : value), 10);
        return Number.isFinite(n) ? n : fallback;
      }

      function parseTimestamp(raw) {
        if (raw == null || raw === "") return NaN;
        const parsed = Date.parse(String(raw).trim());
        return Number.isNaN(parsed) ? NaN : parsed;
      }

      function escapeHtml(str) {
        return String(str)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#39;");
      }

      function normalizeDisplayType(rawType) {
        const key = String(rawType == null ? "" : rawType).trim().toLowerCase().replace(/-/g, "_");
        if (!key) return DEFAULT_IMAGE_TYPE;
        return TYPE_ALIASES[key] || key;
      }

      function getImageTypeForDisplay() {
        if (
          displayType === "status_code" ||
          displayType === "text_length" ||
          displayType === "timestamp_delta" ||
          displayType === "screenshot" ||
          displayType === "latitude_longitude"
        ) {
          return displayType;
        }
        return DEFAULT_IMAGE_TYPE;
      }

      function normalizeStep(row, fallbackStepId) {
        const stepId = parseStepNumber(row.number != null ? row.number : row.id, fallbackStepId);
        const statusCode = parseInt(String(row.status_code == null ? "" : row.status_code), 10);
        return {
          step_id: stepId,
          status_code: Number.isFinite(statusCode) ? statusCode : 0,
          text_length: parseInt(String(row.text_length == null ? "" : row.text_length), 10) || 0,
          timestamp: trimText(row.timestamp),
          screenshot_url: trimText(row.screenshot_url),
          latitude: trimText(row.latitude),
          longitude: trimText(row.longitude),
          error: trimText(row.error),
          url: trimText(row.url),
          src: trimText(row.src),
          _ts: parseTimestamp(row.timestamp),
          _delta_ms: NaN
        };
      }

      function normalizeRows(rows) {
        const normalized = rows.map((row, index) => normalizeStep(row, index)).sort((a, b) => a.step_id - b.step_id);

        let prevTs = NaN;
        normalized.forEach((row) => {
          if (Number.isFinite(row._ts) && Number.isFinite(prevTs)) {
            row._delta_ms = Math.max(0, row._ts - prevTs);
          }
          if (Number.isFinite(row._ts)) {
            prevTs = row._ts;
          }
        });
        return normalized;
      }

      function getInitialType() {
        const url = new URL(window.location.href);
        const fromQuery = normalizeDisplayType(url.searchParams.get("type"));
        if (VALID_TYPES.has(fromQuery)) return fromQuery;
        try {
          const saved = normalizeDisplayType(sessionStorage.getItem(TYPE_STORAGE_KEY));
          if (VALID_TYPES.has(saved)) return saved;
        } catch (error) {}
        return "status_code";
      }

      function normalizeImageFit(raw) {
        const key = String(raw == null ? "" : raw).trim().toLowerCase().replace(/_/g, "-");
        if (key === "scale") return "scale";
        if (key === "no-scale" || key === "noscale") return "no-scale";
        return "";
      }

      function getInitialFit() {
        const url = new URL(window.location.href);
        const fromQuery = normalizeImageFit(url.searchParams.get("fit"));
        if (fromQuery && VALID_FITS.has(fromQuery)) return fromQuery;
        try {
          const saved = normalizeImageFit(sessionStorage.getItem(FIT_STORAGE_KEY));
          if (saved && VALID_FITS.has(saved)) return saved;
        } catch (error) {}
        return "no-scale";
      }

      function syncQueryParams() {
        const url = new URL(window.location.href);
        url.searchParams.set("type", displayType);
        url.searchParams.set("fit", imageFitMode);
        window.history.replaceState({}, "", url);
      }

      function applyDisplayType(nextType, updateUrl) {
        const normalizedType = normalizeDisplayType(nextType);
        displayType = VALID_TYPES.has(normalizedType) ? normalizedType : "status_code";
        typeInputs.forEach((input) => {
          input.checked = input.value === displayType;
        });
        try {
          sessionStorage.setItem(TYPE_STORAGE_KEY, displayType);
        } catch (error) {}
        if (updateUrl) {
          syncQueryParams();
        }
        updateStatus();
        if (hoveredStepId !== null && pendingPointerEvent) {
          const row = getRowForStep(hoveredStepId);
          if (row) {
            renderTooltip(row, pendingPointerEvent.clientX, pendingPointerEvent.clientY);
          } else {
            renderStepNumberOnly(hoveredStepId, pendingPointerEvent.clientX, pendingPointerEvent.clientY);
            scheduleStepDetailFetch(hoveredStepId);
          }
        }
      }

      function syncPresenceImageLayout() {
        if (!image) return;
        if (imageFitMode === "scale") {
          image.classList.add("steps-presence-fit-scale");
          image.classList.remove("steps-presence-fit-noscale");
          image.style.removeProperty("width");
          image.style.removeProperty("height");
        } else {
          image.classList.remove("steps-presence-fit-scale");
          image.classList.add("steps-presence-fit-noscale");
          if (image.naturalWidth && image.naturalHeight) {
            image.style.width = image.naturalWidth + "px";
            image.style.height = image.naturalHeight + "px";
          }
        }
      }

      function applyImageFit(nextFit, updateUrl) {
        const n = normalizeImageFit(nextFit);
        imageFitMode = VALID_FITS.has(n) ? n : "no-scale";
        fitInputs.forEach((input) => {
          input.checked = input.value === imageFitMode;
        });
        if (stageEl) {
          stageEl.classList.toggle("steps-stage-fit-scale", imageFitMode === "scale");
          stageEl.classList.toggle("steps-stage-fit-noscale", imageFitMode === "no-scale");
        }
        syncPresenceImageLayout();
        try {
          sessionStorage.setItem(FIT_STORAGE_KEY, imageFitMode);
        } catch (error) {}
        if (updateUrl) {
          syncQueryParams();
        }
      }

      /** Bitmap cell center in client coordinates (no-scale: 1:1, scale: object-fit cover). */
      function stepCenterClientXY(stepId) {
        if (!image.naturalWidth || !image.naturalHeight) return null;
        const nw = image.naturalWidth;
        const nh = image.naturalHeight;
        const ix = (stepId % nw) + 0.5;
        const iy = Math.floor(stepId / nw) + 0.5;
        const rect = image.getBoundingClientRect();
        const ew = rect.width;
        const eh = rect.height;
        let lx;
        let ly;
        if (imageFitMode === "no-scale") {
          lx = (ix / nw) * ew;
          ly = (iy / nh) * eh;
        } else {
          const s = Math.max(ew / nw, eh / nh);
          const offX = (ew - nw * s) / 2;
          const offY = (eh - nh * s) / 2;
          lx = ix * s + offX;
          ly = iy * s + offY;
        }
        return { x: rect.left + lx, y: rect.top + ly };
      }

      function clientToImagePixel(clientX, clientY) {
        if (!image.naturalWidth || !image.naturalHeight) return null;
        const nw = image.naturalWidth;
        const nh = image.naturalHeight;
        const rect = image.getBoundingClientRect();
        const ew = rect.width;
        const eh = rect.height;
        const lx = clientX - rect.left;
        const ly = clientY - rect.top;
        let bx;
        let by;
        if (imageFitMode === "no-scale") {
          if (lx < 0 || lx > ew || ly < 0 || ly > eh) return null;
          bx = (lx / ew) * nw;
          by = (ly / eh) * nh;
        } else {
          const s = Math.max(ew / nw, eh / nh);
          const offX = (ew - nw * s) / 2;
          const offY = (eh - nh * s) / 2;
          bx = (lx - offX) / s;
          by = (ly - offY) / s;
          if (bx < 0 || bx >= nw || by < 0 || by >= nh) return null;
        }
        const x = Math.max(0, Math.min(nw - 1, Math.floor(bx)));
        const y = Math.max(0, Math.min(nh - 1, Math.floor(by)));
        return { x, y };
      }

      function setTooltipPosition(clientX, clientY) {
        const pad = 16;
        let x = clientX + 18;
        let y = clientY + 18;
        const rect = tooltip.getBoundingClientRect();
        if (x + rect.width > window.innerWidth - pad) x = clientX - rect.width - 18;
        if (y + rect.height > window.innerHeight - pad) y = clientY - rect.height - 18;
        const targetX = Math.max(pad, Math.min(x, window.innerWidth - rect.width - pad));
        const targetY = Math.max(pad, Math.min(y, window.innerHeight - rect.height - pad));
        if (!tooltipPositionReady) {
          tooltip.style.transition = "none";
          tooltip.style.left = targetX + "px";
          tooltip.style.top = targetY + "px";
          tooltipPositionReady = true;
          window.requestAnimationFrame(() => {
            tooltip.style.transition = "";
          });
          return;
        }
        tooltip.style.left = targetX + "px";
        tooltip.style.top = targetY + "px";
      }

      function renderTooltip(step, clientX, clientY) {
        const screenshotHtml = displayType === "screenshot" && step.screenshot_url
          ? `<img class="steps-tooltip-image" src="${escapeHtml(step.screenshot_url)}" alt="step screenshot">`
          : "";
        let metricRow = "";
        if (displayType === "status_code") {
          metricRow = `<div class="steps-tooltip-row"><span class="steps-tooltip-label">status</span><code>${escapeHtml(step.status_code || 0)}</code></div>`;
        } else if (displayType === "text_length") {
          metricRow = `<div class="steps-tooltip-row"><span class="steps-tooltip-label">text_length</span><code>${escapeHtml(step.text_length || 0)}</code></div>`;
        } else if (displayType === "timestamp_delta") {
          metricRow = `<div class="steps-tooltip-row"><span class="steps-tooltip-label">delta_ms</span><code>${escapeHtml(Number.isFinite(step._delta_ms) ? Math.round(step._delta_ms) : "—")}</code></div>`;
        } else if (displayType === "screenshot") {
          metricRow = `<div class="steps-tooltip-row"><span class="steps-tooltip-label">screenshot</span><code>${escapeHtml(step.screenshot_url || "—")}</code></div>`;
        } else if (displayType === "latitude_longitude") {
          metricRow = `<div class="steps-tooltip-row"><span class="steps-tooltip-label">geo</span><code>${escapeHtml((step.latitude || "—") + ", " + (step.longitude || "—"))}</code></div>`;
        } else if (displayType === "error") {
          metricRow = `<div class="steps-tooltip-row"><span class="steps-tooltip-label">error</span><code>${escapeHtml(step.error || "—")}</code></div>`;
        }

        tooltip.innerHTML =
          `<div class="steps-tooltip-row">step <code>${escapeHtml(step.step_id)}</code></div>` +
          metricRow +
          `<div class="steps-tooltip-row"><span class="steps-tooltip-label">url</span><code>${escapeHtml(step.url || "—")}</code></div>` +
          `<div class="steps-tooltip-row"><span class="steps-tooltip-label">src</span><code>${escapeHtml(step.src || "—")}</code></div>` +
          `<div class="steps-tooltip-row"><span class="steps-tooltip-label">time</span><code>${escapeHtml(step.timestamp || "—")}</code></div>` +
          screenshotHtml;
        tooltip.classList.add("visible");
        setTooltipPosition(clientX, clientY);
      }

      function renderNoDataTooltip(stepId, clientX, clientY) {
        tooltip.innerHTML = `<div class="steps-tooltip-row">step <code>${escapeHtml(stepId)}</code> - no data</div>`;
        tooltip.classList.add("visible");
        setTooltipPosition(clientX, clientY);
      }

      function renderStepNumberOnly(stepId, clientX, clientY) {
        tooltip.innerHTML = `<div class="steps-tooltip-row">step <code>${escapeHtml(stepId)}</code></div>`;
        tooltip.classList.add("visible");
        setTooltipPosition(clientX, clientY);
      }

      function clearStepDetailTimer() {
        if (stepDetailTimer !== null) {
          window.clearTimeout(stepDetailTimer);
          stepDetailTimer = null;
        }
      }

      function getRowForStep(stepId) {
        return stepMap.get(stepId) || stepCache.get(stepId) || null;
      }

      function hideTooltip() {
        clearStepDetailTimer();
        hoveredStepId = null;
        tooltip.classList.remove("visible");
        autoCursor.classList.remove("visible");
      }

      function updateStatus() {
        const parts = [displayType];
        const knownSteps = stepMap.size;
        if (knownSteps) parts.push(`known ${knownSteps}`);
        if (latestStepNumber >= 0) parts.push(`latest ${latestStepNumber}`);
        if (image.naturalWidth && image.naturalHeight) parts.push(`image ${image.naturalWidth}x${image.naturalHeight}`);
        statusEl.textContent = parts.join(" · ") || "Loading...";
      }

      function handleImageLoad() {
        if (!image.naturalWidth || !image.naturalHeight) {
          imageReady = false;
          return;
        }
        pixelSource.width = image.naturalWidth;
        pixelSource.height = image.naturalHeight;
        pixelContext.clearRect(0, 0, pixelSource.width, pixelSource.height);
        pixelContext.drawImage(image, 0, 0);
        imageReady = true;
        syncPresenceImageLayout();
        updateStatus();
        if (Number.isFinite(pendingAnchorAfterImageLoad)) {
          const stepId = pendingAnchorAfterImageLoad;
          pendingAnchorAfterImageLoad = null;
          highlightPresenceStep(stepId);
        }
      }

      async function refreshImage() {
        const stamp = Date.now();
        imageReady = false;
        const url = new URL("api/image", baseUrl);
        url.searchParams.set("type", getImageTypeForDisplay());
        url.searchParams.set("v", String(stamp));
        image.src = url.toString();
      }

      async function fetchStep(stepId) {
        if (stepCache.has(stepId)) {
          return stepCache.get(stepId);
        }
        if (pendingStepRequests.has(stepId)) {
          return pendingStepRequests.get(stepId);
        }
        const request = (async () => {
          const response = await fetch(`/api/storage_step/${stepId}/`, { cache: "no-store" });
          if (response.status === 404 || response.status === 502 || response.status === 503 || response.status === 504) {
            return null;
          }
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          const data = normalizeStep(await response.json(), stepId);
          stepCache.set(stepId, data);
          stepMap.set(stepId, data);
          latestStepNumber = Math.max(latestStepNumber, stepId);
          updateStatus();
          return data;
        })();
        pendingStepRequests.set(stepId, request);
        try {
          return await request;
        } finally {
          pendingStepRequests.delete(stepId);
        }
      }

      function scheduleStepDetailFetch(stepId) {
        clearStepDetailTimer();
        stepDetailTimer = window.setTimeout(async () => {
          stepDetailTimer = null;
          if (hoveredStepId !== stepId) {
            return;
          }
          const ev = pendingPointerEvent;
          if (!ev) {
            return;
          }
          let row = getRowForStep(stepId);
          try {
            if (!row) {
              row = await fetchStep(stepId);
            }
          } catch (error) {
            if (hoveredStepId !== stepId) {
              return;
            }
            renderNoDataTooltip(stepId, ev.clientX, ev.clientY);
            return;
          }
          if (hoveredStepId !== stepId) {
            return;
          }
          if (!row) {
            renderNoDataTooltip(stepId, ev.clientX, ev.clientY);
          } else {
            renderTooltip(row, ev.clientX, ev.clientY);
          }
        }, STEP_DETAIL_DELAY_MS);
      }

      function centerForStep(stepId) {
        const p = stepCenterClientXY(stepId);
        if (!p) {
          return { x: window.innerWidth / 2, y: window.innerHeight / 2 };
        }
        return p;
      }

      function trimPresenceAnchors() {
        while (presenceAnchors.length > MAX_PRESENCE_ANCHORS) {
          const oldItem = presenceAnchors.shift();
          if (!oldItem) continue;
          if (oldItem.fadeTimer) window.clearTimeout(oldItem.fadeTimer);
          if (oldItem.removeTimer) window.clearTimeout(oldItem.removeTimer);
          if (oldItem.el && oldItem.el.parentNode) oldItem.el.parentNode.removeChild(oldItem.el);
        }
      }

      function pushPresenceAnchor(point) {
        if (!presenceAnchorsHost || !point) return;
        const anchor = document.createElement("div");
        anchor.className = "steps-presence-anchor";
        anchor.style.left = point.x + "px";
        anchor.style.top = point.y + "px";
        presenceAnchorsHost.appendChild(anchor);
        window.requestAnimationFrame(() => {
          anchor.classList.add("visible");
        });
        const item = { el: anchor, fadeTimer: null, removeTimer: null };
        item.fadeTimer = window.setTimeout(() => {
          anchor.classList.add("fading");
          item.removeTimer = window.setTimeout(() => {
            if (anchor.parentNode) anchor.parentNode.removeChild(anchor);
          }, 550);
        }, PRESENCE_ANCHOR_FADE_MS);
        presenceAnchors.push(item);
        trimPresenceAnchors();
      }

      function pointForStepOnOverlay(stepId) {
        return stepCenterClientXY(stepId);
      }

      async function highlightPresenceStep(stepId) {
        if (!Number.isFinite(stepId) || stepId < 0) return;
        const point = pointForStepOnOverlay(stepId);
        if (!point) {
          pendingAnchorAfterImageLoad = stepId;
          console.log("[steps] presence anchor delayed: image not ready", { stepId });
          return;
        }
        console.log("[steps] presence step highlight", { stepId, x: point.x, y: point.y });
        pushPresenceAnchor(point);
        let row = getRowForStep(stepId);
        if (!row) {
          try {
            row = await fetchStep(stepId);
          } catch (error) {
            row = null;
          }
        }
        hoveredStepId = stepId;
        pendingPointerEvent = { clientX: point.x, clientY: point.y };
        if (row) {
          renderTooltip(row, point.x, point.y);
        } else {
          renderStepNumberOnly(stepId, point.x, point.y);
        }
      }

      function scheduleSocketImageRefresh(stepId) {
        const now = Date.now();
        const elapsedMs = now - lastSocketImageRefreshAt;
        const waitMs = Math.max(0, SOCKET_IMAGE_REFRESH_MIN_INTERVAL_MS - elapsedMs);
        if (socketImageRefreshTimer) return;
        const runRefresh = async () => {
          socketImageRefreshTimer = null;
          try {
            await refreshImage();
            lastSocketImageRefreshAt = Date.now();
            console.log("[steps] refreshImage debounced after presence_step OK", { stepId });
          } catch (error) {}
        };
        if (waitMs <= 0) {
          runRefresh();
        } else {
          socketImageRefreshTimer = window.setTimeout(runRefresh, waitMs);
        }
      }

      function schedulePresenceRefresh(stepId) {
        pendingPresenceStep = stepId;
        if (presenceDebounceTimer) return;
        presenceDebounceTimer = window.setTimeout(async () => {
          const targetStep = pendingPresenceStep;
          pendingPresenceStep = null;
          presenceDebounceTimer = null;
          console.log("[steps] presence_step received", { stepId: targetStep });
          await highlightPresenceStep(targetStep);
          scheduleSocketImageRefresh(targetStep);
        }, SOCKET_PRESENCE_DEBOUNCE_MS);
      }

      function processPointer(event) {
        if (!imageReady || !image.naturalWidth || !image.naturalHeight) {
          hideTooltip();
          return;
        }
        const pixel = clientToImagePixel(event.clientX, event.clientY);
        if (!pixel) {
          hideTooltip();
          return;
        }
        const x = pixel.x;
        const y = pixel.y;
        try {
          const pixel = pixelContext.getImageData(x, y, 1, 1).data;
          const intensity = pixel[0] + pixel[1] + pixel[2];
          if (intensity === 0) {
            hideTooltip();
            return;
          }
          const stepId = y * image.naturalWidth + x;
          hoveredStepId = stepId;
          const row = getRowForStep(stepId);
          if (row) {
            clearStepDetailTimer();
            renderTooltip(row, event.clientX, event.clientY);
          } else {
            renderStepNumberOnly(stepId, event.clientX, event.clientY);
            scheduleStepDetailFetch(stepId);
          }
        } catch (error) {
          const stepId = y * image.naturalWidth + x;
          hoveredStepId = stepId;
          renderStepNumberOnly(stepId, event.clientX, event.clientY);
          scheduleStepDetailFetch(stepId);
        }
      }

      function handlePointer(event) {
        if (autoMode) return;
        pendingPointerEvent = event;
        if (animationFrameId) return;
        animationFrameId = window.requestAnimationFrame(() => {
          animationFrameId = 0;
          if (pendingPointerEvent) {
            processPointer(pendingPointerEvent);
          }
        });
      }

      function pickAutoTarget() {
        if (!imageReady || !image.naturalWidth || !image.naturalHeight) return null;
        const knownStepIds = Array.from(stepMap.keys()).filter((id) => Number.isFinite(id) && id >= 0);
        const maxRasterId = image.naturalWidth * image.naturalHeight - 1;
        if (!knownStepIds.length) {
          return maxRasterId >= 0 ? Math.floor(Math.random() * (maxRasterId + 1)) : null;
        }
        const randomExisting = knownStepIds[Math.floor(Math.random() * knownStepIds.length)];
        if (Math.random() < 0.25) {
          return randomExisting;
        }
        const minId = Math.min(...knownStepIds);
        const maxId = Math.max(...knownStepIds);
        const span = Math.max(1, maxId - minId + 1);
        const expandedSpan = span * AUTO_ID_SPREAD_MULTIPLIER;
        const sigma = expandedSpan / 6;
        const jitter = (Math.random() - 0.5) * sigma;
        const gaussian = Math.sqrt(-2 * Math.log(Math.max(Number.EPSILON, Math.random()))) * Math.cos(2 * Math.PI * Math.random());
        const sampled = Math.round(AUTO_ID_FOCUS + gaussian * sigma + jitter);
        return Math.max(0, Math.min(maxRasterId, sampled));
      }

      function syncAutoTooltip() {
        if (!autoMode || autoTarget == null) return;
        const row = stepMap.get(autoTarget);
        autoCursor.style.left = autoState.x + "px";
        autoCursor.style.top = autoState.y + "px";
        autoCursor.classList.add("visible");
        if (!row) {
          renderStepNumberOnly(autoTarget, autoState.x, autoState.y);
          return;
        }
        renderTooltip(row, autoState.x, autoState.y);
      }

      function animateAuto() {
        if (!autoMode) return;
        autoState.vx += (autoState.targetX - autoState.x) * 0.018;
        autoState.vy += (autoState.targetY - autoState.y) * 0.018;
        autoState.vx *= 0.86;
        autoState.vy *= 0.86;
        autoState.x += autoState.vx;
        autoState.y += autoState.vy;
        syncAutoTooltip();
        autoAnimationFrame = window.requestAnimationFrame(animateAuto);
      }

      function tickAuto() {
        if (!imageReady) return;
        autoTarget = pickAutoTarget();
        if (autoTarget == null) return;
        const point = centerForStep(autoTarget);
        autoState.targetX = point.x;
        autoState.targetY = point.y;
      }

      function stopAuto() {
        autoMode = false;
        autoBtn.setAttribute("aria-pressed", "false");
        autoBtn.textContent = "Auto";
        if (autoTimer) window.clearInterval(autoTimer);
        if (autoAnimationFrame) window.cancelAnimationFrame(autoAnimationFrame);
        autoTimer = null;
        autoAnimationFrame = null;
        autoTarget = null;
        autoCursor.classList.remove("visible");
      }

      function startAuto() {
        if (!imageReady) return;
        autoMode = true;
        autoBtn.setAttribute("aria-pressed", "true");
        autoBtn.textContent = "Auto: on";
        autoTarget = pickAutoTarget();
        const point = centerForStep(autoTarget);
        autoState.x = point.x;
        autoState.y = point.y;
        autoState.targetX = point.x;
        autoState.targetY = point.y;
        autoState.vx = 0;
        autoState.vy = 0;
        tickAuto();
        autoAnimationFrame = window.requestAnimationFrame(animateAuto);
        autoTimer = window.setInterval(tickAuto, 1500);
      }

      function toggleAuto() {
        if (autoMode) {
          stopAuto();
          hideTooltip();
        } else {
          startAuto();
        }
      }

      async function refreshAll() {
        try {
          await refreshImage();
        } catch (error) {
          statusEl.textContent = "Load failed";
        }
      }

      typeInputs.forEach((input) => {
        input.addEventListener("change", (event) => {
          if (event.target.checked) {
            applyDisplayType(event.target.value, true);
          }
        });
      });
      fitInputs.forEach((input) => {
        input.addEventListener("change", (event) => {
          if (event.target.checked) {
            applyImageFit(event.target.value, true);
          }
        });
      });
      autoBtn.addEventListener("click", toggleAuto);
      refreshBtn.addEventListener("click", refreshAll);
      image.addEventListener("load", handleImageLoad);
      image.addEventListener("error", () => {
        imageReady = false;
        statusEl.textContent = "Image unavailable";
      });
      overlay.addEventListener("mousemove", handlePointer);
      overlay.addEventListener("mouseleave", () => {
        if (!autoMode) {
          hideTooltip();
        }
      });

      const BF_POLL_MS = 8000;
      const bfMeta = document.getElementById("steps-bf-meta");
      const bfState = document.getElementById("steps-bf-state");
      const bfStep = document.getElementById("steps-bf-step");
      const bfPage = document.getElementById("steps-bf-page");
      const bfProcessed = document.getElementById("steps-bf-processed");
      const bfSkipped = document.getElementById("steps-bf-skipped");
      const bfSleep = document.getElementById("steps-bf-sleep");
      const bfTimeout = document.getElementById("steps-bf-timeout");
      const bfDelta = document.getElementById("steps-bf-delta");
      const bfDetail = document.getElementById("steps-bf-detail");

      function renderStepsBackfill(payload) {
        if (!bfState || !bfStep || !bfPage || !bfProcessed || !bfSkipped || !bfSleep || !bfTimeout || !bfDelta || !bfDetail) return;
        const data = payload || {};
        const st = String(data.state || "idle");
        const stepNum = data.last_id ? String(data.last_id) : "—";
        const cur = Number(data.current_page || 0);
        const tot = Number(data.total_pages || 0);
        const proc = Number(data.processed || 0);
        const skip = Number(data.skipped || 0);
        const sleep = Number(data.backfill_sleep);
        const timeout = Number(data.backfill_timeout);
        const delta = Number(data.step_delta_sec);
        const lastUrl = data.last_url ? escapeHtml(String(data.last_url)) : "—";
        const lastErr = data.last_error ? escapeHtml(String(data.last_error)) : "";
        const updated = data.updated_at ? escapeHtml(String(data.updated_at)) : "no data";
        if (bfMeta) bfMeta.textContent = data.error ? "error" : (data.exists ? updated : "idle");
        bfState.textContent = st;
        bfState.className = "steps-backfill-value is-" + st;
        bfStep.textContent = stepNum;
        bfPage.textContent = cur + " / " + tot;
        bfProcessed.textContent = String(proc);
        bfSkipped.textContent = String(skip);
        bfSleep.textContent = Number.isFinite(sleep) ? sleep.toFixed(1) + "s" : "—";
        bfTimeout.textContent = Number.isFinite(timeout) ? timeout.toFixed(1) + "s" : "—";
        bfDelta.textContent = Number.isFinite(delta) && delta > 0 ? delta.toFixed(2) + "s" : "—";
        if (data.error) {
          bfDetail.textContent = "Status unavailable: " + data.error;
          return;
        }
        if (!data.exists) {
          bfDetail.textContent = "No data yet";
          return;
        }
        bfDetail.innerHTML = lastErr ? ("Last error: " + lastErr) : ("Last URL: " + lastUrl);
      }

      async function refreshStepsBackfill() {
        if (!bfState) return;
        try {
          const response = await fetch("/api/backfill/status/", {
            cache: "no-store",
            credentials: "include",
          });
          const payload = await response.json();
          renderStepsBackfill(payload);
          console.log("[steps] backfill status", payload);
        } catch (err) {
          renderStepsBackfill({ error: "fetch failed", exists: false, state: "idle" });
          console.log("[steps] backfill status fetch failed", err);
        }
      }

      const socket = io(window.location.origin, { transports: ["websocket", "polling"] });
      socket.on("connect", () => {
        console.log("[steps] socket connected", { id: socket.id });
      });
      socket.on("disconnect", (reason) => {
        console.log("[steps] socket disconnected", { reason });
      });
      socket.on("presence_step", (payload) => {
        const stepId = parseInt(String((payload || {}).step ?? ""), 10);
        if (!Number.isFinite(stepId)) return;
        console.log("[steps] socket presence_step", payload);
        schedulePresenceRefresh(stepId);
      });

      applyDisplayType(getInitialType(), false);
      applyImageFit(getInitialFit(), false);
      syncQueryParams();
      refreshAll();
      refreshStepsBackfill();
      window.setInterval(refreshImage, 300000);
      window.setInterval(refreshStepsBackfill, BF_POLL_MS);
    </script>
  </body>
</html>
"""


def write_snapshot(output_dir: Path, image_type: str, png_bytes: bytes) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / image_snapshot_name(image_type)).write_bytes(png_bytes)


def build_image_url(image_type: str) -> str:
    return f"{DEFAULT_IMAGE_URL}?type={urllib.parse.quote(image_type)}"


async def fetch_snapshot(image_type: str) -> ImageSnapshot:
    png_bytes = await asyncio.to_thread(fetch_bytes, build_image_url(image_type))
    width, height = parse_png_dimensions(png_bytes)
    await asyncio.to_thread(write_snapshot, DEFAULT_OUTPUT_DIR, image_type, png_bytes)
    return ImageSnapshot(width=width, height=height, png_bytes=png_bytes)


async def refresh_presence() -> None:
    image_urls = {image_type: build_image_url(image_type) for image_type in SUPPORTED_IMAGE_TYPES}
    async with state_lock:
        snapshots = dict(state.snapshots or {})
        payload = dict(state.steps_payload) if state.steps_payload else None

    image_results = await asyncio.gather(
        *[
            asyncio.to_thread(fetch_bytes, image_url)
            for image_url in image_urls.values()
        ],
        return_exceptions=True,
    )
    csv_result = await asyncio.gather(
        asyncio.to_thread(fetch_csv_rows, DEFAULT_STEPS_CSV_URL),
        return_exceptions=True,
    )

    errors = []
    for image_type, result in zip(image_urls.keys(), image_results):
        if isinstance(result, Exception):
            errors.append(f"{image_type}: {result}")
            continue
        width, height = parse_png_dimensions(result)
        await asyncio.to_thread(write_snapshot, DEFAULT_OUTPUT_DIR, image_type, result)
        snapshots[image_type] = ImageSnapshot(width=width, height=height, png_bytes=result)

    csv_rows = csv_result[0]
    if isinstance(csv_rows, Exception):
        errors.append(f"csv: {csv_rows}")
    else:
        payload = {
            "fields": list(csv_rows[0].keys()) if csv_rows else [],
            "returned_lines": len(csv_rows),
            "total_lines": len(csv_rows),
            "data": csv_rows,
        }

    if not snapshots:
        err_text = "; ".join(errors) if errors else "no per-fetch details"
        raise RuntimeError(f"No image snapshots available after refresh: {err_text}")
    if payload is None:
        err_text = "; ".join(errors) if errors else "no per-fetch details"
        raise RuntimeError(f"Steps payload not available after refresh: {err_text}")

    async with state_lock:
        state.snapshots = snapshots
        state.steps_payload = payload
        state.updated_at = datetime.now(timezone.utc).isoformat()
        state.error = "; ".join(errors) if errors else None


async def refresh_loop() -> None:
    while True:
        try:
            await refresh_presence()
            async with state_lock:
                loaded_types = sorted((state.snapshots or {}).keys())
            logger.info("Presence updated for types: %s", ", ".join(loaded_types))
        except urllib.error.URLError as exc:
            message = f"Failed to fetch steps image payloads: {exc}"
            logger.exception(message)
            async with state_lock:
                state.error = message
        except ValueError as exc:
            message = f"Invalid image response from {DEFAULT_IMAGE_URL}: {exc}"
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
        default_snapshot = (state.snapshots or {}).get(DEFAULT_IMAGE_TYPE)
        return {
            "status": "ok" if default_snapshot and default_snapshot.png_bytes else "warming_up",
            "width": default_snapshot.width if default_snapshot else 1,
            "height": default_snapshot.height if default_snapshot else 1,
            "types": sorted((state.snapshots or {}).keys()),
            "updated_at": state.updated_at,
            "error": state.error,
        }


@app.get("/api/latest")
async def api_latest(type: str = DEFAULT_IMAGE_TYPE):
    image_type = normalize_image_type(type)
    should_refresh = False
    async with state_lock:
        should_refresh = state.steps_payload is None
    if should_refresh:
        try:
            await refresh_presence()
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Steps payload not ready yet: {exc}")
    async with state_lock:
        if state.steps_payload is None:
            raise HTTPException(status_code=503, detail="Steps payload not ready yet")
        payload = dict(state.steps_payload)
        payload["type"] = image_type
        return JSONResponse(content=payload)


@app.get("/api/image")
async def api_image(type: str = DEFAULT_IMAGE_TYPE) -> Response:
    image_type = normalize_image_type(type)
    async with state_lock:
        snapshot = (state.snapshots or {}).get(image_type)
    if snapshot is None or not snapshot.png_bytes:
        try:
            snapshot = await fetch_snapshot(image_type)
            async with state_lock:
                snapshots = dict(state.snapshots or {})
                snapshots[image_type] = snapshot
                state.snapshots = snapshots
                state.updated_at = datetime.now(timezone.utc).isoformat()
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Presence image not ready yet: {exc}")
    async with state_lock:
        snapshot = (state.snapshots or {}).get(image_type)
        if snapshot is None or not snapshot.png_bytes:
            raise HTTPException(status_code=503, detail="Presence image not ready yet")
        return Response(content=snapshot.png_bytes, media_type="image/png")
