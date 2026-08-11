from __future__ import annotations

import os
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult


class InMemorySpanExporter(SpanExporter):
    def __init__(self) -> None:
        self._spans: list = []

    def export(self, spans) -> SpanExportResult:
        self._spans.extend(spans)
        return SpanExportResult.SUCCESS

    def get_finished_spans(self) -> list:
        return list(self._spans)

    def clear(self) -> None:
        self._spans.clear()

    def shutdown(self) -> None:
        self.clear()


try:
    from langfuse import get_client, observe

    LANGFUSE_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - chỉ dùng khi chưa cài requirements
    LANGFUSE_SDK_AVAILABLE = False

    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func

        return decorator

    class _DummyClient:
        def update_current_trace(self, **kwargs: Any) -> None:
            return None

        def update_current_generation(self, **kwargs: Any) -> None:
            return None

    def get_client():
        return _DummyClient()


# Initialize OpenTelemetry Tracer Provider
_otel_provider = TracerProvider()
_memory_exporter = InMemorySpanExporter()
_otel_provider.add_span_processor(SimpleSpanProcessor(_memory_exporter))
trace.set_tracer_provider(_otel_provider)
_otel_tracer = trace.get_tracer("day13-ai-observability", "1.0.0")


def get_otel_tracer() -> trace.Tracer:
    return _otel_tracer


def get_otel_spans() -> list:
    return _memory_exporter.get_finished_spans()


def get_langfuse_client():
    return get_client()


def tracing_enabled() -> bool:
    return LANGFUSE_SDK_AVAILABLE and bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )
