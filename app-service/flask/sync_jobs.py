import logging
import math
import os
import sys
import time

import requests
from rq.decorators import job
from rq import get_current_job
from rq_helpers import redis_connection

logging.basicConfig(
    level=logging.INFO,
    format="[sync] %(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

REMOTE_DATA_URL = os.getenv("REMOTE_DATA_URL", "https://data.jamming-bot.arthew0.online")
REMOTE_STORAGE_URL = os.getenv("REMOTE_STORAGE_URL", "https://storage.jamming-bot.arthew0.online")
REMOTE_TAGS_URL = os.getenv("REMOTE_TAGS_URL", "https://tags.jamming-bot.arthew0.online")

DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://data_service:8010")
STORAGE_SERVICE_URL = os.getenv("STORAGE_SERVICE_URL", "http://storage_service:7781")
TAGS_SERVICE_URL = os.getenv("TAGS_SERVICE_URL", "http://tags_service:8000")

REQUEST_TIMEOUT = 60
BATCH_SIZE = 500


def _update_progress(self_job, iteration, total, extra=None):
    meta = {
        "num_iterations": total,
        "iteration": iteration,
        "percent": round(iteration / max(total, 1) * 100, 1),
    }
    if extra:
        meta.update(extra)
    self_job.meta["progress"] = meta
    self_job.save_meta()


@job("default", connection=redis_connection, timeout=3600, result_ttl=86400)
def sync_bot_urls():
    """Pull URLs from remote data-service into local data-service."""
    self_job = get_current_job()
    self_job.meta["type"] = "sync_bot"
    self_job.save_meta()

    remote_stats = requests.get(
        f"{REMOTE_DATA_URL}/api/urls/stats", timeout=REQUEST_TIMEOUT
    ).json()
    remote_total = remote_stats["total"]
    logger.info("Remote bot URLs total: %d", remote_total)

    total_pages = max(1, math.ceil(remote_total / BATCH_SIZE))
    total_inserted = 0
    total_skipped = 0

    for page in range(1, total_pages + 1):
        resp = requests.get(
            f"{REMOTE_DATA_URL}/api/urls",
            params={"page": page, "per_page": BATCH_SIZE},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        rows = data.get("data", [])

        if not rows:
            break

        import_resp = requests.post(
            f"{DATA_SERVICE_URL}/api/urls/import",
            json={"items": rows},
            timeout=REQUEST_TIMEOUT,
        )
        import_resp.raise_for_status()
        result = import_resp.json()
        total_inserted += result.get("inserted", 0)
        total_skipped += result.get("skipped", 0)

        _update_progress(self_job, page, total_pages)
        logger.info("Bot URLs page %d/%d: inserted=%d skipped=%d", page, total_pages, result.get("inserted", 0), result.get("skipped", 0))

    return {
        "service": "bot",
        "inserted": total_inserted,
        "skipped": total_skipped,
        "remote_total": remote_total,
    }


@job("default", connection=redis_connection, timeout=7200, result_ttl=86400)
def sync_storage_steps():
    """Pull missing steps from remote storage-service into local."""
    self_job = get_current_job()
    self_job.meta["type"] = "sync_storage"
    self_job.save_meta()

    remote_ids_resp = requests.get(
        f"{REMOTE_STORAGE_URL}/get/ids", timeout=REQUEST_TIMEOUT
    )
    remote_ids_resp.raise_for_status()
    remote_ids = remote_ids_resp.json().get("data", [])
    remote_ids_str = [str(n) for n in remote_ids]
    logger.info("Remote storage step IDs: %d", len(remote_ids_str))

    missing = []
    for i in range(0, len(remote_ids_str), BATCH_SIZE):
        batch = remote_ids_str[i : i + BATCH_SIZE]
        resp = requests.post(
            f"{STORAGE_SERVICE_URL}/exists/batch",
            json={"numbers": batch},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        missing.extend(resp.json().get("missing", []))

    logger.info("Missing steps to sync: %d", len(missing))

    if not missing:
        _update_progress(self_job, 1, 1)
        return {"service": "storage", "synced": 0, "total_remote": len(remote_ids)}

    synced = 0
    errors = 0
    total = len(missing)

    for idx, step_number in enumerate(missing, 1):
        try:
            step_resp = requests.get(
                f"{REMOTE_STORAGE_URL}/get/step/{step_number}",
                timeout=REQUEST_TIMEOUT,
            )
            if step_resp.status_code == 404:
                continue
            step_resp.raise_for_status()
            step_data = step_resp.json()

            store_resp = requests.post(
                f"{STORAGE_SERVICE_URL}/store",
                json=step_data,
                timeout=REQUEST_TIMEOUT,
            )
            store_resp.raise_for_status()
            synced += 1
        except Exception as e:
            errors += 1
            logger.warning("Failed to sync step %s: %s", step_number, e)

        if idx % 10 == 0 or idx == total:
            _update_progress(self_job, idx, total)

    return {
        "service": "storage",
        "synced": synced,
        "errors": errors,
        "total_remote": len(remote_ids),
    }


@job("default", connection=redis_connection, timeout=3600, result_ttl=86400)
def sync_tags():
    """Pull tags from remote tags-service into local."""
    self_job = get_current_job()
    self_job.meta["type"] = "sync_tags"
    self_job.save_meta()

    remote_tags_resp = requests.get(
        f"{REMOTE_TAGS_URL}/api/v1/tags/", timeout=REQUEST_TIMEOUT
    )
    remote_tags_resp.raise_for_status()
    remote_tags = remote_tags_resp.json()
    logger.info("Remote tags total: %d", len(remote_tags))

    total_batches = max(1, math.ceil(len(remote_tags) / BATCH_SIZE))
    total_created = 0
    total_updated = 0

    for batch_idx in range(total_batches):
        start = batch_idx * BATCH_SIZE
        batch = remote_tags[start : start + BATCH_SIZE]

        items = [{"name": t["name"], "count": t["count"]} for t in batch]
        resp = requests.post(
            f"{TAGS_SERVICE_URL}/api/v1/tags/sync/",
            json={"items": items},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        result = resp.json()
        total_created += result.get("created", 0)
        total_updated += result.get("updated", 0)

        _update_progress(self_job, batch_idx + 1, total_batches)
        logger.info(
            "Tags batch %d/%d: created=%d updated=%d",
            batch_idx + 1, total_batches,
            result.get("created", 0), result.get("updated", 0),
        )

    return {
        "service": "tags",
        "created": total_created,
        "updated": total_updated,
        "remote_total": len(remote_tags),
    }
