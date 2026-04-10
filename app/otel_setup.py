"""
otel_setup.py — OpenTelemetry provider configuration.

Configures the global TracerProvider at startup. Two modes:
  - OTEL_EXPORTER_OTLP_ENDPOINT set → exports spans to Jaeger/Langfuse/Phoenix
  - Not set → provider configured but no exporter (spans emitted, dropped)

All code is fail-safe: missing packages degrade gracefully, never crash the app.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("civitae")
_configured = False


def setup_otel() -> None:
    """Configure OTel TracerProvider once at startup. Safe to call multiple times."""
    global _configured
    if _configured:
        return
    _configured = True

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider

        resource = Resource.create({
            "service.name": "civitae",
            "service.version": "0.1.0",
            "civitae.governance": "six_fold_flame",
        })
        provider = TracerProvider(resource=resource)

        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").rstrip("/")
        if endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                from opentelemetry.sdk.trace.export import BatchSpanProcessor
                exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
                provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info("OTel: OTLP exporter configured → %s", endpoint)
            except ImportError:
                logger.warning(
                    "OTEL_EXPORTER_OTLP_ENDPOINT is set but "
                    "opentelemetry-exporter-otlp-proto-http is not installed — "
                    "spans will be dropped"
                )

        trace.set_tracer_provider(provider)
        logger.debug("OTel: TracerProvider ready (exporter: %s)", endpoint or "none")

    except ImportError:
        logger.debug("opentelemetry-sdk not installed — OTel tracing disabled")


def get_tracer(name: str = "civitae") -> object:
    """Return the configured tracer. Falls back to no-op if OTel unavailable."""
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        return _NoOpTracer()


class _NoOpTracer:
    """Fallback when opentelemetry-api is not installed at all."""

    class _NoOpSpan:
        def set_attribute(self, *a, **kw): pass
        def record_exception(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass

    def start_as_current_span(self, name: str, **kwargs):
        return self._NoOpSpan()
