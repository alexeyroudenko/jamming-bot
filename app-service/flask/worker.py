import os
import sys
import logging

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.rq import RqIntegration

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

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
    w = Worker(["default"], connection=redis_connection)
    w.work(logging_level=logging.INFO)
