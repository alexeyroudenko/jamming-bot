# OpenTelemetry / Jaeger tracing setup and RQ context propagation.

import os
import logging
from functools import wraps

logger = logging.getLogger(__name__)

_initialized = False


def init_telemetry(service_name=None):
    """Initialize OpenTelemetry TracerProvider and export to Jaeger (OTLP). Idempotent."""
    global _initialized
    if _initialized:
        return
    if os.getenv("OTEL_TRACING_ENABLED", "0") != "1":
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.propagate import set_global_textmap
        from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

        set_global_textmap(TraceContextTextMapPropagator())
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4318").rstrip("/")
        if not endpoint.endswith("/v1/traces"):
            endpoint = f"{endpoint}/v1/traces"
        name = service_name or os.getenv("OTEL_SERVICE_NAME", "app-service")

        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)
        _initialized = True
        logger.info("OpenTelemetry tracing initialized (service=%s, endpoint=%s)", name, endpoint)
    except Exception as e:
        logger.warning("OpenTelemetry init failed: %s", e)


def get_trace_context_for_rq():
    """Return a dict suitable for job.meta to propagate trace context to RQ workers."""
    if os.getenv("OTEL_TRACING_ENABLED", "0") != "1":
        return {}
    try:
        from opentelemetry.propagate import inject
        carrier = {}
        inject(carrier)
        return carrier
    except Exception:
        return {}


def inject_trace_context_into_job(job):
    """Write current trace context into job.meta so the worker can continue the trace."""
    if not job:
        return
    ctx = get_trace_context_for_rq()
    if not ctx:
        return
    try:
        job.meta["trace_carrier"] = ctx
        job.save_meta()
    except Exception as e:
        logger.debug("Could not inject trace context into job: %s", e)


# Map RQ function name -> job type for Jaeger (matches job.meta['type'])
_JOB_TYPE_MAP = {
    "dostep": "step",
    "do_geo": "geo",
    "analyze": "analyze",
    "do_screenshot": "screenshot",
    "clean_tags": "clean_tags",
    "add_tags": "add_tags",
    "add_tags_from_steps": "add_tags_from_steps",
    "save": "save",
    "wait": "wait",
    "clean_tsv_data": "cleaning",
    "add": "add",
    "pulse": "pulse",
}


def set_step_span_attributes(step_number=None, step_url=None):
    """Set step-related attributes on the current OTEL span so Jaeger can filter by step."""
    if os.getenv("OTEL_TRACING_ENABLED", "0") != "1":
        return
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        if not span or not span.is_recording():
            return
        if step_number is not None:
            span.set_attribute("step.number", str(step_number))
        if step_url is not None:
            span.set_attribute("step.url", str(step_url)[:2048])
    except Exception as e:
        logger.debug("set_step_span_attributes failed: %s", e)


def with_trace_context(f):
    """Decorator for RQ job functions: restore trace context from job.meta and run in a span."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        job = None
        try:
            from rq import get_current_job
            job = get_current_job()
        except Exception:
            pass
        if not job or os.getenv("OTEL_TRACING_ENABLED", "0") != "1":
            return f(*args, **kwargs)

        carrier = job.meta.get("trace_carrier") or {}
        if not carrier:
            return f(*args, **kwargs)

        try:
            from opentelemetry import trace
            from opentelemetry.propagate import extract

            ctx = extract(carrier)
            tracer = trace.get_tracer(__name__)
            job_type = _JOB_TYPE_MAP.get(f.__name__, f.__name__)
            with tracer.start_as_current_span(
                f"rq.{f.__name__}",
                context=ctx,
                kind=trace.SpanKind.SERVER,
            ) as span:
                if span.is_recording():
                    span.set_attribute("rq.job_type", job_type)
                    if job.id:
                        span.set_attribute("rq.job_id", job.id)
                return f(*args, **kwargs)
        except Exception as e:
            logger.debug("Trace context restore failed: %s", e)
            return f(*args, **kwargs)

    return wrapper
