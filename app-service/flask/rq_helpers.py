# project/server/main/rq_helpers.py

import redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq.utils import as_text

import config
from datetime import datetime, timedelta

# get redis connection
redis_connection = redis.from_url(config.ProductionConfig.REDIS_URL)

# get rq queue with redis connection
queue = Queue(connection=redis_connection)
# Heavy screenshot jobs — consumed by worker-screenshots (see deployment.yaml)
screenshot_queue = Queue("screenshots", connection=redis_connection)

ALL_QUEUES = (queue, screenshot_queue)


def fetch_job_by_id(job_id):
    """Load job from Redis by id regardless of RQ queue origin (default vs screenshots)."""
    if not job_id:
        return None
    try:
        return Job.fetch(
            job_id,
            connection=redis_connection,
            serializer=queue.serializer,
        )
    except NoSuchJobError:
        return None


# get job ids, given rq.JobRegistry
def get_job_ids(job_registry):
    return job_registry.get_job_ids()


def _ids_newest_first(registry):
    """Return job ids from a sorted-set RQ registry in newest-first order (ZREVRANGE)."""
    return [as_text(j) for j in registry.connection.zrevrange(registry.key, 0, -1)]


def _finished_with_scores(registry):
    """Return [(job_id, completion_ts)] from FinishedJobRegistry, newest-first."""
    raw = registry.connection.zrevrange(registry.key, 0, -1, withscores=True)
    return [(as_text(j), float(s)) for j, s in raw]


def get_all_job_ids():
    """Return job ids across all RQ queues in newest-first order.

    - Active registries (started/queued/failed/deferred/scheduled) come first
      so live work is always visible on page 0.
    - Finished jobs from default + screenshots are merged by completion timestamp
      (FinishedJobRegistry score = unix ts), so screenshot-queue jobs are not
      hidden behind a long tail of older default-queue finishes.
    """
    active = []
    for q in ALL_QUEUES:
        active.extend(_ids_newest_first(q.started_job_registry))
        # queued is a Redis LIST (FIFO) — reverse to put newest enqueues first
        active.extend(list(reversed(q.job_ids)))
        active.extend(_ids_newest_first(q.failed_job_registry))
        active.extend(_ids_newest_first(q.deferred_job_registry))
        active.extend(_ids_newest_first(q.scheduled_job_registry))

    finished = []
    for q in ALL_QUEUES:
        finished.extend(_finished_with_scores(q.finished_job_registry))
    finished.sort(key=lambda x: x[1], reverse=True)

    chunks = active + [jid for jid, _ in finished]
    seen = set()
    ordered = []
    for jid in chunks:
        if jid not in seen:
            seen.add(jid)
            ordered.append(jid)
    return ordered

# get job given its id
def get_job_from_id(job_id):
    return fetch_job_by_id(job_id)

# get all jobs
def get_all_jobs():
    all_jobs = []
    for job_id in get_all_job_ids():
        job = get_job_from_id(job_id)
        if job is not None:
            all_jobs.append(job)
    return all_jobs


def get_all_jobs_paginated(limit=200, offset=0):
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 200
    try:
        offset = int(offset)
    except (TypeError, ValueError):
        offset = 0
    limit = max(1, min(limit, 5000))
    offset = max(0, offset)
    all_job_ids = get_all_job_ids()
    selected_ids = all_job_ids[offset: offset + limit]
    jobs = []
    for job_id in selected_ids:
        job = get_job_from_id(job_id)
        if job is not None:
            jobs.append(job)
    return jobs, len(all_job_ids)


