# project/server/main/rq_helpers.py

import redis
from rq import Queue
import config
from datetime import datetime, timedelta

# get redis connection
redis_connection = redis.from_url(config.ProductionConfig.REDIS_URL)

# get rq queue with redis connection
queue = Queue(connection=redis_connection)

# get job ids, given rq.JobRegistry
def get_job_ids(job_registry):
    return job_registry.get_job_ids()

def get_all_job_ids():
    all_job_ids = []
    all_job_ids.extend(get_job_ids(queue.started_job_registry))
    all_job_ids.extend(queue.job_ids) # queued job ids
    all_job_ids.extend(get_job_ids(queue.failed_job_registry))
    all_job_ids.extend(get_job_ids(queue.deferred_job_registry))
    all_job_ids.extend(get_job_ids(queue.finished_job_registry))
    all_job_ids.extend(get_job_ids(queue.scheduled_job_registry))
    return all_job_ids

# get job given its id
def get_job_from_id(job_id):
    job = queue.fetch_job(job_id)
    return job

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


