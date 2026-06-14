"""
Distributed Tracer - Implements span lifecycle controls (start_span, end_span).

Creates trace span entries with precise timing, parent linking, and service
attribution. Spans are buffered in the TraceCollector for batch persistence.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.services.observability.trace_manager import (
    get_trace_id,
    generate_span_id,
    push_span,
    pop_span,
    get_parent_span_id,
)

logger = logging.getLogger("observability.distributed_tracer")


class SpanContext:
    """Represents an active trace span with timing metadata."""

    def __init__(
        self,
        trace_id: str,
        span_id: str,
        name: str,
        service_name: str = "forest-fire-detection",
        parent_span_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.name = name
        self.service_name = service_name
        self.parent_span_id = parent_span_id
        self.metadata = metadata or {}
        self.start_time = datetime.now(timezone.utc)
        self._start_ns = time.perf_counter_ns()
        self.end_time: Optional[datetime] = None
        self.duration_ms: float = 0.0
        self.status: str = "success"
        self.error_message: Optional[str] = None

    def finish(self, status: str = "success", error_message: Optional[str] = None) -> None:
        """Mark the span as finished, computing duration."""
        self.end_time = datetime.now(timezone.utc)
        elapsed_ns = time.perf_counter_ns() - self._start_ns
        self.duration_ms = round(elapsed_ns / 1_000_000, 2)
        self.status = status
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the span to a dictionary for database persistence."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "service_name": self.service_name,
            "start_time": self.start_time,
            "end_time": self.end_time or datetime.now(timezone.utc),
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error_message": self.error_message,
            "metadata_json": self.metadata,
        }


class DistributedTracer:
    """
    Manages the lifecycle of distributed trace spans.
    Integrates with the TraceManager for context propagation
    and the TraceCollector for batch persistence.
    """

    def start_span(
        self,
        name: str,
        service_name: str = "forest-fire-detection",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SpanContext:
        """
        Start a new trace span, pushing it onto the context stack.
        Returns a SpanContext that must be finished when the operation completes.
        """
        trace_id = get_trace_id() or "unknown"
        parent_span_id = get_parent_span_id()
        span_id = generate_span_id()

        push_span(span_id)

        span = SpanContext(
            trace_id=trace_id,
            span_id=span_id,
            name=name,
            service_name=service_name,
            parent_span_id=parent_span_id,
            metadata=metadata,
        )

        logger.debug(f"Started span '{name}' (trace={trace_id}, span={span_id})")
        return span

    def end_span(
        self,
        span: SpanContext,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Finish a span and pop it from the context stack.
        Returns the span data dictionary for collector buffering.
        """
        span.finish(status=status, error_message=error_message)
        pop_span()

        logger.debug(f"Ended span '{span.name}' (duration={span.duration_ms}ms, status={status})")
        return span.to_dict()


# Module-level singleton
distributed_tracer = DistributedTracer()
