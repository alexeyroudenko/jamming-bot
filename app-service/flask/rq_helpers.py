# project/server/main/rq_helpers.py

import redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

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

def get_all_job_ids():
    chunks = []
    for q in ALL_QUEUES:
        chunks.extend(get_job_ids(q.started_job_registry))
        chunks.extend(q.job_ids)
        chunks.extend(get_job_ids(q.failed_job_registry))
        chunks.extend(get_job_ids(q.deferred_job_registry))
        chunks.extend(get_job_ids(q.finished_job_registry))
        chunks.extend(get_job_ids(q.scheduled_job_registry))
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


