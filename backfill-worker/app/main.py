"""
Backfill worker: iterates visited URLs from data-service (by id ascending),
checks which ones are missing in storage-service, fetches the page and
sends it through app-service in silent mode for full processing.
"""

import asyncio
import json
import logging
import os
import socket
import sys
import time
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

USER_AGENT = "JammingBot/2.1 (+https://jamming-bot.arthew0.online/)"
BACKFILL_STATUS_KEY = os.getenv("BACKFILL_STATUS_KEY", "backfill:status")
BACKFILL_STATUS_TTL = int(os.getenv("BACKFILL_STATUS_TTL", "86400"))
redis_client = Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
)


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
    resp = requests.post(
        f"{STORAGE_SERVICE}/exists/batch",
        json={"numbers": ids},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["missing"]


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


async def fetch_page(url: str):
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(
            url,
            headers={
                "Accept-Language": "en-US, en;q=0.5",
                "Accept-Charset": "utf-8",
                "Accept-Encoding": "gzip",
                "User-Agent": USER_AGENT,
            },
            timeout=PAGE_TIMEOUT,
        )
    return response


def send_to_app_service(row: dict, html: str, text: str, ip: str, status_code: int):
    requests.post(
        f"{APP_SERVICE}/bot/step/",
        data={
            "number": str(row["id"]),
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
    try:
        response = await fetch_page(url)
    except Exception as e:
        logger.warning("fetch failed id=%s url=%s: %s", row["id"], url, e)
        update_backfill_status(last_id=row["id"], last_url=url, last_error=f"fetch failed: {e}")
        return False

    if response.status_code != 200:
        logger.debug("skip id=%s status=%s url=%s", row["id"], response.status_code, url)
        update_backfill_status(
            last_id=row["id"],
            last_url=url,
            last_error=f"non-200 status: {response.status_code}",
        )
        return False

    content_type = response.headers.get("content-type", "")
    if "html" not in content_type.lower():
        logger.debug("skip id=%s non-html url=%s", row["id"], url)
        update_backfill_status(last_id=row["id"], last_url=url, last_error=f"non-html content-type: {content_type}")
        return False

    html = response.content.decode("utf-8", errors="replace")
    text = get_text_from_html(html)
    ip = resolve_ip(url)

    try:
        send_to_app_service(row, html, text, ip, response.status_code)
        logger.info("processed id=%s url=%s", row["id"], url)
        update_backfill_status(last_id=row["id"], last_url=url, last_error="")
        return True
    except Exception as e:
        logger.warning("app-service failed id=%s: %s", row["id"], e)
        update_backfill_status(last_id=row["id"], last_url=url, last_error=f"app-service failed: {e}")
        return False


async def main():
    logger.info("backfill-worker started (batch=%s, sleep=%.1fs)", BATCH_SIZE, SLEEP_BETWEEN)

    page = 1
    total_processed = 0
    total_skipped = 0
    update_backfill_status(
        state="running",
        started_at=now_ts(),
        finished_at="",
        current_page=0,
        total_pages=0,
        processed=0,
        skipped=0,
        last_id="",
        last_url="",
        last_error="",
    )

    while True:
        try:
            rows, pagination = get_visited_urls(page, per_page=BATCH_SIZE)
        except Exception as e:
            logger.error("data-service error page=%s: %s", page, e)
            update_backfill_status(state="failed", current_page=page, last_error=f"data-service error: {e}")
            break

        if not rows:
            break

        ids = [str(r["id"]) for r in rows]
        try:
            missing = set(check_missing(ids))
        except Exception as e:
            logger.error("storage exists/batch error: %s", e)
            update_backfill_status(
                state="failed",
                current_page=page,
                total_pages=pagination.get("total_pages", 0),
                processed=total_processed,
                skipped=total_skipped,
                last_error=f"storage exists/batch error: {e}",
            )
            break

        skipped = len(ids) - len(missing)
        total_skipped += skipped
        update_backfill_status(
            state="running",
            current_page=page,
            total_pages=pagination.get("total_pages", 0),
            processed=total_processed,
            skipped=total_skipped,
        )

        for row in rows:
            if str(row["id"]) not in missing:
                continue
            ok = await process_row(row)
            if ok:
                total_processed += 1
                update_backfill_status(
                    state="running",
                    current_page=page,
                    total_pages=pagination.get("total_pages", 0),
                    processed=total_processed,
                    skipped=total_skipped,
                )
            await asyncio.sleep(SLEEP_BETWEEN)

        logger.info(
            "page %s/%s done — processed=%s skipped_existing=%s",
            page, pagination["total_pages"], total_processed, total_skipped,
        )

        if page >= pagination["total_pages"]:
            break
        page += 1

    logger.info("backfill-worker finished: processed=%s skipped=%s", total_processed, total_skipped)
    update_backfill_status(
        state="finished",
        current_page=page,
        processed=total_processed,
        skipped=total_skipped,
        finished_at=now_ts(),
        last_error="",
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        logger.exception("backfill-worker crashed: %s", exc)
        update_backfill_status(state="failed", finished_at=now_ts(), last_error=str(exc))
        raise
