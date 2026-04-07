"""
Backfill worker: iterates visited URLs from data-service (by id ascending, paged),
checks which ones are missing in storage-service, fetches the page and
sends it through app-service in silent mode for full processing.

Within each batch, URL order defaults to round-robin across hostnames (see BACKFILL_URL_ORDER).
"""

import asyncio
import json
import logging
import os
import random
import socket
import sys
import time
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse

import httpx
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from PIL import Image
from redis import Redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("backfill")

DATA_SERVICE = os.getenv("DATA_SERVICE_URL", "http://data-service")
STORAGE_SERVICE = os.getenv("STORAGE_SERVICE_URL", "http://storage-service")
APP_SERVICE = os.getenv("APP_SERVICE_URL", "http://app-service")

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))
SLEEP_BETWEEN = float(os.getenv("SLEEP_BETWEEN", "2.0"))
PAGE_TIMEOUT = int(os.getenv("PAGE_TIMEOUT", "10"))
# Cap fetched HTML before decode/BS4 — pathological pages otherwise OOM the pod (limit often 2–4Gi).
MAX_HTML_BYTES = int(os.getenv("MAX_HTML_BYTES", str(6 * 1024 * 1024)))
# round_robin: shuffle within hostname, then interleave hosts; id: preserve data-service order
BACKFILL_URL_ORDER = os.getenv("BACKFILL_URL_ORDER", "round_robin").strip().lower()
BACKFILL_CYCLE_SLEEP = float(os.getenv("BACKFILL_CYCLE_SLEEP", "20"))
BACKFILL_STEP_BASE = int(os.getenv("BACKFILL_STEP_BASE", "100000"))
BACKFILL_MIN_ID = int(os.getenv("BACKFILL_MIN_ID", "0"))
BACKFILL_MAX_ID = int(os.getenv("BACKFILL_MAX_ID", "2147483647"))
_BACKFILL_SEED = os.getenv("BACKFILL_RANDOM_SEED", "").strip()
if _BACKFILL_SEED:
    random.seed(_BACKFILL_SEED)

USER_AGENT = "JammingBot/2.1 (+https://jamming-bot.arthew0.online/)"
BACKFILL_STATUS_KEY = os.getenv("BACKFILL_STATUS_KEY", "backfill:status")
BACKFILL_STATUS_TTL = int(os.getenv("BACKFILL_STATUS_TTL", "86400"))
redis_client = Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
)

# Local cache of storage presence PNG (refreshed every N cycles or on missing/empty file).
PRESENCE_PNG_PATH = os.getenv("PRESENCE_PNG_PATH", "/tmp/backfill/presence.png")


def _presence_export_url() -> str:
    explicit = os.getenv("PRESENCE_EXPORT_URL", "").strip()
    if explicit:
        return explicit
    return f"{STORAGE_SERVICE.rstrip('/')}/export/img?width=0&type=presence"


def _presence_png_cache_valid() -> bool:
    try:
        return os.path.isfile(PRESENCE_PNG_PATH) and os.path.getsize(PRESENCE_PNG_PATH) > 0
    except OSError:
        return False


def fetch_presence_png() -> None:
    """Download presence raster from storage-service (or PRESENCE_EXPORT_URL) into PRESENCE_PNG_PATH."""
    url = _presence_export_url()
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    with open(PRESENCE_PNG_PATH, "wb") as f:
        f.write(resp.content)
    logger.info(
        "presence png fetched %s -> %s (%s bytes)",
        url,
        PRESENCE_PNG_PATH,
        len(resp.content),
    )


BLACK_PIXEL_MAX_TRIES = int(os.getenv("BLACK_PIXEL_MAX_TRIES", "8000"))
# Parallel HTML fetches (async httpx) per inner-loop iteration; presence PNG steps stay sequential.
# Default from env; live value from Redis key fetch_concurrency (1–32), set from /ctrl/.
_FETCH_CONCURRENCY_DEFAULT = max(1, min(32, int(os.getenv("FETCH_CONCURRENCY", "10"))))


def current_fetch_concurrency() -> int:
    try:
        raw = redis_client.get("fetch_concurrency")
        if raw is None:
            return _FETCH_CONCURRENCY_DEFAULT
        if isinstance(raw, bytes):
            raw = raw.decode()
        v = int(float(raw))
        return max(1, min(32, v))
    except (TypeError, ValueError):
        return _FETCH_CONCURRENCY_DEFAULT


def _pixel_is_black(value: object) -> bool:
    """Presence PNG may be L (int) or RGB/RGBA tuples."""
    if value == 0:
        return True
    if value == (0, 0, 0):
        return True
    if isinstance(value, (tuple, list)):
        if len(value) >= 3 and value[0] == 0 and value[1] == 0 and value[2] == 0:
            return True
        if len(value) == 1 and value[0] == 0:
            return True
    return False


def pick_black_pixel_linear_index(img: Image.Image) -> tuple[int, int, int]:
    """
    Random tries, then full scan for a black pixel; if none, random cell.
    Returns (px, py, linear_index px + py * width).
    """
    width, height = img.size
    cap = max(1, min(BLACK_PIXEL_MAX_TRIES, width * height))
    for _ in range(cap):
        px = random.randint(0, width - 1)
        py = random.randint(0, height - 1)
        if _pixel_is_black(img.getpixel((px, py))):
            return px, py, px + py * width
    for py in range(height):
        for px in range(width):
            if _pixel_is_black(img.getpixel((px, py))):
                return px, py, px + py * width
    px = random.randint(0, width - 1)
    py = random.randint(0, height - 1)
    logger.warning(
        "presence image has no black pixel; using random cell px=%s py=%s",
        px,
        py,
    )
    return px, py, px + py * width


def mark_presence_pixel_used(img: Image.Image, px: int, py: int) -> None:
    """Mutate image so this cell is unlikely to read as black next time."""
    mode = img.mode
    if mode == "L":
        img.putpixel((px, py), 255)
    elif mode == "RGB":
        img.putpixel((px, py), (255, 0, 0))
    elif mode == "RGBA":
        img.putpixel((px, py), (255, 0, 0, 255))
    else:
        try:
            img.putpixel((px, py), 255)
        except Exception:
            logger.debug("could not mark pixel in mode %s", mode)


def _redis_float(key: str, default: float) -> float:
    try:
        raw = redis_client.get(key)
        if raw is None:
            return default
        if isinstance(raw, bytes):
            raw = raw.decode()
        return float(raw)
    except (TypeError, ValueError, AttributeError):
        return default


def current_backfill_sleep() -> float:
    return max(0.0, _redis_float("backfill_sleep", SLEEP_BETWEEN))


def current_page_timeout() -> float:
    t = _redis_float("backfill_timeout", float(PAGE_TIMEOUT))
    return 1.0 if t <= 0 else t


def backfill_is_active() -> bool:
    """When False, worker idles (Redis key backfill_active, set from /ctrl/). Default True if unset."""
    try:
        raw = redis_client.get("backfill_active")
        if raw is None:
            return True
        if isinstance(raw, bytes):
            raw = raw.decode()
        return float(raw) >= 0.5
    except (TypeError, ValueError, AttributeError):
        return True


def now_ts() -> str:
    return str(datetime.now().timestamp())


def update_backfill_status(**fields):
    mapping = {}
    for key, value in fields.items():
        if isinstance(value, (dict, list, tuple)):
            mapping[key] = json.dumps(value, default=str)
        elif value is None:
            mapping[key] = ""
        else:
            mapping[key] = str(value)
    mapping["updated_at"] = now_ts()
    try:
        redis_client.hset(BACKFILL_STATUS_KEY, mapping=mapping)
        redis_client.expire(BACKFILL_STATUS_KEY, BACKFILL_STATUS_TTL)
    except Exception as exc:
        logger.warning("backfill status update failed: %s", exc)


def _read_status_float(field: str) -> float | None:
    try:
        raw = redis_client.hget(BACKFILL_STATUS_KEY, field)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        return float(raw)
    except (TypeError, ValueError, AttributeError):
        return None


def update_backfill_step_progress(step_number: str, url: str, error_text: str) -> None:
    now_value = float(now_ts())
    prev_value = _read_status_float("last_step_ts")
    delta_value = None
    if prev_value is not None:
        delta_value = max(0.0, now_value - prev_value)
    update_backfill_status(
        last_id=step_number,
        last_url=url,
        last_error=error_text,
        prev_step_ts=prev_value if prev_value is not None else "",
        last_step_ts=now_value,
        step_delta_sec=delta_value if delta_value is not None else "",
    )


def get_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser", from_encoding="utf-8")
    header = soup.find("header")
    if header:
        header.decompose()
    footer = soup.find("footer")
    if footer:
        footer.decompose()
    text_out = ""
    for h2 in soup.find_all("h2"):
        node = h2
        while True:
            node = node.nextSibling
            if node is None:
                break
            if isinstance(node, NavigableString):
                text_out += node.strip().replace("\n", "").replace("\r", "")
                break
            if isinstance(node, Tag):
                if node.name in {"h1", "h2", "h3", "h4", "h5"}:
                    break
                txt = node.get_text(strip=True).strip().replace("\n", "").replace("\r", "")
                if len(txt) > 0:
                    text_out += txt
                    break
    if text_out == "":
        paragraphs = [p.get_text() for p in soup.find_all("p")]
        if len(paragraphs) > 0:
            text_out = paragraphs[0]
    return text_out


def get_visited_urls(page: int, per_page: int = 100):
    resp = requests.get(
        f"{DATA_SERVICE}/api/urls",
        params={"visited": 1, "page": page, "per_page": per_page},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["data"], data["pagination"]


def check_missing(ids: list[str]) -> list[str]:
    last_error = None
    for attempt in range(4):
        try:
            resp = requests.post(
                f"{STORAGE_SERVICE}/exists/batch",
                json={"numbers": ids},
                timeout=20,
            )
            resp.raise_for_status()
            return resp.json()["missing"]
        except Exception as exc:
            last_error = exc
            if attempt >= 3:
                break
            time.sleep(0.8 * (attempt + 1))
    raise last_error


def backfill_step_number(row_id: str | int) -> str:
    return str(BACKFILL_STEP_BASE + int(row_id))


def id_in_range(row_id: str | int) -> bool:
    value = int(row_id)
    return BACKFILL_MIN_ID <= value <= BACKFILL_MAX_ID


def row_hostname(row: dict) -> str:
    h = row.get("hostname")
    if h is not None and str(h).strip():
        return str(h).strip().lower()
    parsed = urlparse(row.get("url") or "")
    return (parsed.hostname or "").lower() or "_"


def order_rows_round_robin(rows: list[dict]) -> list[dict]:
    """Shuffle within each host, shuffle host order, then take one from each host per round."""
    by_host: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_host[row_hostname(row)].append(row)
    for host in by_host:
        random.shuffle(by_host[host])
    hosts = list(by_host.keys())
    random.shuffle(hosts)
    out: list[dict] = []
    while True:
        progressed = False
        for h in hosts:
            bucket = by_host[h]
            if bucket:
                out.append(bucket.pop())
                progressed = True
        if not progressed:
            break
    return out


def order_rows_for_backfill(rows: list[dict], missing: set[str]) -> list[dict]:
    to_process = [r for r in rows if backfill_step_number(r["id"]) in missing]
    if BACKFILL_URL_ORDER == "id":
        return to_process
    return order_rows_round_robin(to_process)


def resolve_ip(url: str) -> str:
    try:
        hostname = urlparse(url).hostname
        if hostname:
            infos = socket.getaddrinfo(hostname, None, socket.AF_INET)
            if infos:
                return infos[0][4][0]
    except (socket.gaierror, OSError, ValueError):
        pass
    return "0"


async def fetch_page(url: str, timeout: float | None = None):
    sec = float(timeout if timeout is not None else current_page_timeout())
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(
            url,
            headers={
                "Accept-Language": "en-US, en;q=0.5",
                "Accept-Charset": "utf-8",
                "Accept-Encoding": "gzip",
                "User-Agent": USER_AGENT,
            },
            timeout=sec,
        )
    return response


def send_to_app_service(row: dict, html: str, text: str, ip: str, status_code: int):
    step_number = backfill_step_number(row["id"])
    requests.post(
        f"{APP_SERVICE}/bot/step/",
        data={
            "number": step_number,
            "url": row["url"],
            "src": row.get("src_url", ""),
            "ip": ip,
            "status_code": str(status_code),
            "timestamp": str(datetime.now().timestamp()),
            "text": text,
            "html": html,
            "silent": "1",
        },
        timeout=30,
    )


async def process_row(row: dict):
    url = row["url"]
    step_number = backfill_step_number(row["id"])
    try:
        response = await fetch_page(url, timeout=current_page_timeout())
    except Exception as e:
        logger.warning("fetch failed id=%s step=%s url=%s: %s", row["id"], step_number, url, e)
        update_backfill_step_progress(step_number, url, f"fetch failed: {e}")
        return False

    if response.status_code != 200:
        logger.debug("skip id=%s step=%s status=%s url=%s", row["id"], step_number, response.status_code, url)
        update_backfill_step_progress(step_number, url, f"non-200 status: {response.status_code}")
        return False

    content_type = response.headers.get("content-type", "")
    if "html" not in content_type.lower():
        logger.debug("skip id=%s step=%s non-html url=%s", row["id"], step_number, url)
        update_backfill_step_progress(step_number, url, f"non-html content-type: {content_type}")
        return False

    raw = response.content
    if len(raw) > MAX_HTML_BYTES:
        logger.warning(
            "truncating html id=%s step=%s url=%s size=%s -> %s bytes",
            row["id"],
            step_number,
            url,
            len(raw),
            MAX_HTML_BYTES,
        )
        raw = raw[:MAX_HTML_BYTES]
    html = raw.decode("utf-8", errors="replace")
    del raw
    text = get_text_from_html(html)
    ip = resolve_ip(url)

    try:
        send_to_app_service(row, html, text, ip, response.status_code)
        logger.info("processed id=%s step=%s url=%s", row["id"], step_number, url)
        update_backfill_step_progress(step_number, url, "")
        return True
    except Exception as e:
        logger.warning("app-service failed id=%s step=%s: %s", row["id"], step_number, e)
        update_backfill_step_progress(step_number, url, f"app-service failed: {e}")
        return False


async def main():
    logger.info(
        "backfill-worker started (batch=%s, sleep=%.1fs, fetch_concurrency=%s, url_order=%s, step_base=%s, id_range=%s..%s)",
        BATCH_SIZE,
        SLEEP_BETWEEN,
        current_fetch_concurrency(),
        BACKFILL_URL_ORDER,
        BACKFILL_STEP_BASE,
        BACKFILL_MIN_ID,
        BACKFILL_MAX_ID,
    )

    total_processed = 0
    total_skipped = 0
    cycle = 0

    while True:
        while not backfill_is_active():
            update_backfill_status(
                state="paused",
                finished_at=now_ts(),
                last_error="backfill выключен (backfill_active=0, /ctrl/)",
            )
            await asyncio.sleep(2.0)

        cycle += 1
        page = 1
        cycle_processed = 0
        cycle_skipped = 0
        total_pages = 0
        update_backfill_status(
            state="running",
            started_at=now_ts(),
            finished_at="",
            cycle=cycle,
            current_page=0,
            total_pages=0,
            processed=total_processed,
            skipped=total_skipped,
            cycle_processed=cycle_processed,
            cycle_skipped=cycle_skipped,
            last_id="",
            last_url="",
            last_error="",
        )

        while True:
            # Refresh periodically, or immediately if cache missing/empty (cold start).
            if cycle % 64 == 0 or not _presence_png_cache_valid():
                fetch_presence_png()

            fc = current_fetch_concurrency()
            total_pages = 0
            batch: list[dict] = []
            for _ in range(fc):
                with Image.open(PRESENCE_PNG_PATH) as img:
                    width, height = img.size
                    total_pages = width * height
                    px, py, pixwel_number = pick_black_pixel_linear_index(img)
                    mark_presence_pixel_used(img, px, py)
                    img.save(PRESENCE_PNG_PATH)

                row_url = f"{DATA_SERVICE.rstrip('/')}/data/{pixwel_number}/"
                try:
                    row_resp = requests.get(row_url, timeout=30)
                    row_resp.raise_for_status()
                    data = row_resp.json()
                    batch.append(
                        {
                            "id": data["id"],
                            "url": data["url"],
                        }
                    )
                except (requests.RequestException, ValueError, KeyError) as e:
                    logger.warning("data-service row %s: %s", row_url, e)

            if not batch:
                cycle += 1
                await asyncio.sleep(current_backfill_sleep())
                continue

            results = await asyncio.gather(*(process_row(r) for r in batch), return_exceptions=True)
            for row, res in zip(batch, results):
                if isinstance(res, Exception):
                    logger.exception(
                        "process_row failed id=%s url=%s: %s",
                        row.get("id"),
                        row.get("url"),
                        res,
                    )

            n = len(batch)
            total_processed = cycle
            page = cycle
            cycle += n
            update_backfill_status(
                state="running",
                cycle=cycle,
                current_page=page,
                total_pages=total_pages,
                processed=total_processed,
                skipped=total_skipped,
                cycle_processed=cycle_processed,
                cycle_skipped=cycle_skipped,
            )

            await asyncio.sleep(current_backfill_sleep())
            logger.info(
                "batch n=%s fetch_concurrency=%s cycle=%s page=%s/%s total_processed=%s total_skipped=%s",
                n,
                fc,
                cycle,
                page,
                total_pages,
                total_processed,
                total_skipped,
            )

            if page >= total_pages:
                break
            page += 1

        logger.info(
            "backfill cycle %s finished: cycle_processed=%s cycle_skipped=%s; sleeping %.1fs",
            cycle,
            cycle_processed,
            cycle_skipped,
            BACKFILL_CYCLE_SLEEP,
        )
        update_backfill_status(
            state="idle",
            cycle=cycle,
            current_page=page,
            total_pages=total_pages,
            processed=total_processed,
            skipped=total_skipped,
            cycle_processed=cycle_processed,
            cycle_skipped=cycle_skipped,
            finished_at=now_ts(),
            last_error="",
        )
        await asyncio.sleep(max(1.0, BACKFILL_CYCLE_SLEEP))


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
            break
        except Exception as exc:
            logger.exception("backfill-worker crashed: %s", exc)
            try:
                update_backfill_status(state="failed", finished_at=now_ts(), last_error=str(exc))
            except Exception:
                pass
            logger.exception("backfill-worker sleep 45s")
            time.sleep(45)
