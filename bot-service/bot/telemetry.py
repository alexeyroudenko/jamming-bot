"""OpenTelemetry → Jaeger (OTLP HTTP) for bot-service only. No propagation to Flask."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_initialized = False


def init_telemetry() -> None:
    """TracerProvider + OTLP export. Idempotent. No-op unless OTEL_TRACING_ENABLED=1."""
    global _initialized
    if _initialized:
        return
    if os.getenv("OTEL_TRACING_ENABLED", "0") != "1":
        return
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
        from opentelemetry.propagate import set_global_textmap

        set_global_textmap(TraceContextTextMapPropagator())
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4318").rstrip("/")
        if not endpoint.endswith("/v1/traces"):
            endpoint = f"{endpoint}/v1/traces"
        service_name = os.getenv("OTEL_SERVICE_NAME", "bot-service")
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)
        _initialized = True
        logger.info("OpenTelemetry tracing enabled (service=%s, endpoint=%s)", service_name, endpoint)
    except Exception as e:
        logger.warning("OpenTelemetry init failed: %s", e)


def get_tracer():
    from opentelemetry import trace

    return trace.get_tracer("bot-service", "1.0.0")


@contextmanager
def root_do_step_span(step_number: int):
    """Root span for one do_step() execution."""
    if os.getenv("OTEL_TRACING_ENABLED", "0") != "1":
        yield
        return
    tracer = get_tracer()
    with tracer.start_as_current_span(
        "bot.do_step",
        attributes={"step.number": int(step_number)},
    ):
        yield


@contextmanager
def event_span(event_name: str):
    """Span for notify_about_eventp (includes HTTP child if send_events)."""
    if os.getenv("OTEL_TRACING_ENABLED", "0") != "1":
        yield
        return
    tracer = get_tracer()
    name = str(event_name)[:240]
    # Имя span — то, что Jaeger показывает в списке операций (не только атрибуты).
    span_name = f"bot event {name}"[:256]
    with tracer.start_as_current_span(span_name, attributes={"event.name": name}):
        yield


@contextmanager
def step_post_span(step_number: int):
    """Span for POST /bot/step/."""
    if os.getenv("OTEL_TRACING_ENABLED", "0") != "1":
        yield
        return
    tracer = get_tracer()
    with tracer.start_as_current_span(
        "bot.step_post",
        attributes={"step.number": int(step_number)},
    ):
        yield


@contextmanager
def http_client_span(url: str):
    """Client span for requests.post to Flask."""
    if os.getenv("OTEL_TRACING_ENABLED", "0") != "1":
        yield
        return
    from urllib.parse import urlparse
    from opentelemetry.trace import SpanKind

    tracer = get_tracer()
    parsed = urlparse(url)
    path = (parsed.path or "")[:512]
    attrs = {
        "http.method": "POST",
        "http.url": f"{parsed.scheme}://{parsed.netloc}{path}"[:768],
        "net.peer.name": parsed.hostname or "",
    }
    with tracer.start_as_current_span("http.client", kind=SpanKind.CLIENT, attributes=attrs):
        yield


def _query_operation(kwargs, args) -> str:
    q = kwargs.get("query")
    if q is None and args:
        q = args[0]
    if not q:
        return "UNKNOWN"
    return (str(q).strip().split()[0] or "UNKNOWN")[:32]


@contextmanager
def db_span(kwargs, args):
    """Span for one SQLite call via databases library."""
    if os.getenv("OTEL_TRACING_ENABLED", "0") != "1":
        yield
        return
    tracer = get_tracer()
    op = _query_operation(kwargs, args)
    with tracer.start_as_current_span(
        "db.sqlite",
        attributes={"db.system": "sqlite", "db.operation": op},
    ):
        yield
