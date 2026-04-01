# OpenTelemetry / Jaeger tracing setup and RQ context propagation.

import os
import json
import logging
from contextlib import contextmanager
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
    """Return a dict suitable for job.meta to propagate trace context to RQ workers.
    All values are strings so the carrier survives JSON/Redis serialization."""
    if os.getenv("OTEL_TRACING_ENABLED", "0") != "1":
        return {}
    try:
        from opentelemetry.propagate import inject
        carrier = {}
        inject(carrier)
        return {k: str(v) for k, v in carrier.items() if v is not None}
    except Exception:
        return {}


def inject_trace_context_into_job(job):
    """Write current trace context into job.meta so the worker can continue the trace.
    Stored as JSON string so RQ/Redis serialization cannot break nested dict."""
    if not job:
        return
    ctx = get_trace_context_for_rq()
    if not ctx:
        return
    try:
        job.meta["trace_carrier"] = json.dumps(ctx)
        job.save_meta()
    except Exception as e:
        logger.warning("Could not inject trace context into job %s: %s", getattr(job, "id", None), e)


def enqueue_with_trace(queue, connection, func, *args, timeout=90, result_ttl=270, **kwargs):
    """Enqueue an RQ job with trace context in meta *before* pushing to the queue,
    so the worker always sees the carrier (avoids race with save_meta() after delay()).
    Returns the Job. Falls back to func.delay(*args, **kwargs) when tracing is disabled."""
    carrier = get_trace_context_for_rq()
    if not carrier:
        return func.delay(*args, **kwargs)
    try:
        from rq.job import Job
        job = Job.create(
            func=func,
            args=args,
            kwargs=kwargs,
            connection=connection,
            timeout=timeout,
            result_ttl=result_ttl,
            meta={"trace_carrier": json.dumps(carrier)},
            origin=queue.name,
        )
        queue.enqueue_job(job)
        return job
    except Exception as e:
        logger.warning("enqueue_with_trace failed, falling back to delay: %s", e)
        return func.delay(*args, **kwargs)


# Map RQ function name -> job type for Jaeger (matches job.meta['type'])
_JOB_TYPE_MAP = {
    "dostep": "step",
    "do_geo": "geo",
    "analyze": "analyze",
    "do_screenshot": "screenshot",
    "image_analyze": "image_analyze",
    "do_storage": "storage",
    "clean_tags": "clean_tags",
    "add_tags": "add_tags",
    "add_tags_from_steps": "add_tags_from_steps",
    "save": "save",
    "wait": "wait",
    "clean_tsv_data": "cleaning",
    "add": "add",
    "pulse": "pulse",
}


@contextmanager
def step_span(step_number=None, step_url=None):
    """Context manager: create a span 'bot.step' so job spans (dostep, analyze, do_screenshot) appear as children in Jaeger."""
    if os.getenv("OTEL_TRACING_ENABLED", "0") != "1":
        yield
        return
    try:
        from opentelemetry import trace
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("bot.step") as span:
            if span.is_recording():
                if step_number is not None:
                    span.set_attribute("step.number", str(step_number))
                if step_url is not None:
                    span.set_attribute("step.url", str(step_url)[:2048])
            yield
    except Exception as e:
        logger.debug("step_span failed: %s", e)
        raise


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

        raw = job.meta.get("trace_carrier")
        if isinstance(raw, str):
            try:
                carrier = json.loads(raw)
            except (ValueError, TypeError):
                carrier = {}
        else:
            carrier = raw or {}
        if not carrier:
            logger.debug("No trace_carrier for job id=%s (meta keys=%s)", getattr(job, "id", None), list(job.meta.keys()) if job else [])
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
                result = f(*args, **kwargs)
            # Flush so parent (rq.*) span is exported with its children (e.g. GET),
            # avoiding "invalid parent span IDs" / clock skew warning in Jaeger
            try:
                provider = trace.get_tracer_provider()
                if hasattr(provider, "force_flush"):
                    provider.force_flush(timeout_millis=3000)
            except Exception:
                pass
            return result
        except Exception as e:
            logger.debug("Trace context restore failed: %s", e)
            return f(*args, **kwargs)

    return wrapper
