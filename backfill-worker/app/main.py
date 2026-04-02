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

    html = response.content.decode("utf-8", errors="replace")
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
        "backfill-worker started (batch=%s, sleep=%.1fs, url_order=%s, step_base=%s, id_range=%s..%s)",
        BATCH_SIZE,
        SLEEP_BETWEEN,
        BACKFILL_URL_ORDER,
        BACKFILL_STEP_BASE,
        BACKFILL_MIN_ID,
        BACKFILL_MAX_ID,
    )

    total_processed = 0
    total_skipped = 0
    cycle = 0

    while True:
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
            try:
                rows, pagination = get_visited_urls(page, per_page=BATCH_SIZE)
                total_pages = int(pagination.get("total_pages", 0))
            except Exception as e:
                logger.error("data-service error page=%s: %s", page, e)
                update_backfill_status(state="failed", cycle=cycle, current_page=page, last_error=f"data-service error: {e}")
                break

            if not rows:
                break
            if int(rows[0]["id"]) > BACKFILL_MAX_ID:
                logger.info("page=%s starts above max id (%s > %s), stopping cycle", page, rows[0]["id"], BACKFILL_MAX_ID)
                break

            rows = [r for r in rows if id_in_range(r["id"])]
            if not rows:
                if page >= total_pages:
                    break
                page += 1
                continue

            ids = [backfill_step_number(r["id"]) for r in rows]
            try:
                missing = set(check_missing(ids))
            except Exception as e:
                logger.error("storage exists/batch error: %s", e)
                update_backfill_status(
                    state="failed",
                    cycle=cycle,
                    current_page=page,
                    total_pages=total_pages,
                    processed=total_processed,
                    skipped=total_skipped,
                    cycle_processed=cycle_processed,
                    cycle_skipped=cycle_skipped,
                    last_error=f"storage exists/batch error: {e}",
                )
                break

            skipped = len(ids) - len(missing)
            total_skipped += skipped
            cycle_skipped += skipped
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

            for row in order_rows_for_backfill(rows, missing):
                ok = await process_row(row)
                if ok:
                    total_processed += 1
                    cycle_processed += 1
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
                "cycle %s page %s/%s done - total_processed=%s total_skipped=%s cycle_processed=%s cycle_skipped=%s",
                cycle,
                page,
                total_pages,
                total_processed,
                total_skipped,
                cycle_processed,
                cycle_skipped,
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
