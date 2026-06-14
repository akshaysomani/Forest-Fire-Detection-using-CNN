"""
Span Manager - Decorator helper to automatically trace service method calls.

Provides a simple @traced decorator that wraps async functions with
distributed tracing span creation and completion.
"""

import logging
import functools
from typing import Optional, Dict, Any, Callable
from app.services.observability.distributed_tracer import distributed_tracer
from app.services.observability.trace_collector import trace_collector

logger = logging.getLogger("observability.span_manager")


def traced(
    name: Optional[str] = None,
    service_name: str = "forest-fire-detection",
    metadata: Optional[Dict[str, Any]] = None,
) -> Callable:
    """
    Decorator that automatically wraps an async function with a trace span.

    Usage:
        @traced(name="process_image")
        async def process_image(db, image_id):
            ...

    The span is automatically started before the function executes
    and finished (with success or error status) after it completes.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            span_name = name or f"{func.__module__}.{func.__qualname__}"
            span = distributed_tracer.start_span(
                name=span_name,
                service_name=service_name,
                metadata=metadata,
            )

            try:
                result = await func(*args, **kwargs)
                span_data = distributed_tracer.end_span(span, status="success")
                trace_collector.collect(span_data)
                return result
            except Exception as e:
                span_data = distributed_tracer.end_span(
                    span,
                    status="error",
                    error_message=str(e),
                )
                trace_collector.collect(span_data)
                raise

        return wrapper

    return decorator
