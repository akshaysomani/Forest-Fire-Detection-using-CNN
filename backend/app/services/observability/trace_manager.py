"""
Trace Manager - Propagates tracing context (trace ID, span stack) across async boundaries.

Uses Python contextvars for async-safe trace context propagation within
the request lifecycle. Manages the span hierarchy stack.
"""

import uuid
import logging
from contextvars import ContextVar
from typing import Optional, List

logger = logging.getLogger("observability.trace_manager")

# Context variables for trace propagation
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
span_stack_var: ContextVar[List[str]] = ContextVar("span_stack", default=[])


def generate_trace_id() -> str:
    """Generate a unique trace ID."""
    return str(uuid.uuid4())


def generate_span_id() -> str:
    """Generate a unique span ID."""
    return uuid.uuid4().hex[:16]


def get_trace_id() -> Optional[str]:
    """Get the current trace ID from context."""
    return trace_id_var.get()


def set_trace_id(tid: str) -> None:
    """Set the trace ID in the current async context."""
    trace_id_var.set(tid)


def get_current_span_id() -> Optional[str]:
    """Get the current (top of stack) span ID."""
    stack = span_stack_var.get()
    return stack[-1] if stack else None


def push_span(span_id: str) -> None:
    """Push a new span ID onto the span stack."""
    current_stack = span_stack_var.get()
    new_stack = current_stack + [span_id]
    span_stack_var.set(new_stack)


def pop_span() -> Optional[str]:
    """Pop the current span from the stack, returning its ID."""
    current_stack = span_stack_var.get()
    if current_stack:
        new_stack = current_stack[:-1]
        popped = current_stack[-1]
        span_stack_var.set(new_stack)
        return popped
    return None


def get_parent_span_id() -> Optional[str]:
    """Get the parent span ID (second from top of stack)."""
    stack = span_stack_var.get()
    return stack[-2] if len(stack) >= 2 else None


def reset_trace_context() -> None:
    """Reset all trace context variables for a new request."""
    trace_id_var.set(None)
    span_stack_var.set([])
