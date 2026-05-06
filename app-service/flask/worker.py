import os
import sys
import logging

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.rq import RqIntegration

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

# Sentry transport drowns the worker log in SSL/connection retry warnings when
# the ingest endpoint flaps. We only care about ERRORs from urllib3 retry layer.
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)
logging.getLogger("urllib3.util.retry").setLevel(logging.ERROR)

def _traces_sampler(ctx):
    return 1.0


if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            LoggingIntegration(level=logging.INFO, event_level=logging.WARNING),
            RqIntegration(),
        ],
        enable_logs=True,
        environment=ENVIRONMENT,
        traces_sampler=_traces_sampler,
        profiles_sample_rate=1.0,
        send_default_pii=False,
    )

from rq import Worker
from rq_helpers import redis_connection

if __name__ == "__main__":
    raw = (os.getenv("RQ_QUEUE_NAMES") or "default").strip()
    queue_names = [q.strip() for q in raw.split(",") if q.strip()]
    if not queue_names:
        queue_names = ["default"]
    w = Worker(queue_names, connection=redis_connection)
    w.work(logging_level=logging.INFO)
