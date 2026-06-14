"""
Observability Middleware - Global FastAPI middleware for request instrumentation.

Automatically generates/propagates correlation IDs, sets context variables,
records request performance metrics (latency, status, path), and logs
structured request/response information.
"""

import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.services.observability.structured_logger import (
    generate_correlation_id,
    set_correlation_id,
    correlation_id_var,
    request_path_var,
    request_method_var,
)
from app.services.observability.trace_manager import (
    generate_trace_id,
    set_trace_id,
    reset_trace_context,
)
from app.services.observability.metrics_registry import metrics_registry
from app.services.observability.availability_tracker import availability_tracker

logger = logging.getLogger("observability.middleware")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that instruments every incoming HTTP request with:
    - Correlation ID generation/propagation (X-Correlation-ID header)
    - Trace ID generation for distributed tracing
    - Request latency measurement
    - In-memory metric counter updates
    - Structured JSON request logging
    - Availability ping recording
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Reset trace context for new request
        reset_trace_context()

        # Extract or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = generate_correlation_id()

        # Set context variables for structured logging
        set_correlation_id(correlation_id)
        request_path_var.set(request.url.path)
        request_method_var.set(request.method)

        # Generate trace ID for distributed tracing
        trace_id = generate_trace_id()
        set_trace_id(trace_id)

        # Start timing
        start_ns = time.perf_counter_ns()

        # Process the request
        status_code = 500  # Default in case of unhandled exception
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            logger.error(f"Request failed: {e}", exc_info=True)
            raise
        finally:
            # Calculate elapsed time
            elapsed_ns = time.perf_counter_ns() - start_ns
            latency_ms = round(elapsed_ns / 1_000_000, 2)

            # Update in-memory counters
            metrics_registry.increment("api.total_requests")
            metrics_registry.increment(f"api.status.{status_code}")
            if status_code >= 400:
                metrics_registry.increment("api.error_requests")

            # Record availability ping
            availability_tracker.record_ping(
                success=status_code < 500,
                service="api",
                latency_ms=latency_ms,
            )

            # Log the request (skip health check endpoints to reduce noise)
            if request.url.path not in ("/health", "/api/v1/openapi.json"):
                logger.info(f"{request.method} {request.url.path} -> {status_code} ({latency_ms}ms)")

        # Inject correlation ID into response headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Trace-ID"] = trace_id

        return response
