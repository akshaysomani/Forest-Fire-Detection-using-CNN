"""
Structured JSON Logger with Correlation ID Context Propagation.

Provides a centralized logging formatter that outputs structured JSON log lines
with automatic correlation ID injection from the current request context.
Uses Python's contextvars for async-safe propagation across the request lifecycle.
"""
import json
import logging
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Context variables for request-scoped correlation data
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
request_path_var: ContextVar[Optional[str]] = ContextVar("request_path", default=None)
request_method_var: ContextVar[Optional[str]] = ContextVar("request_method", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for request tracing."""
    return str(uuid.uuid4())


def get_correlation_id() -> Optional[str]:
    """Retrieve the current correlation ID from context."""
    return correlation_id_var.get()


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID in the current async context."""
    correlation_id_var.set(cid)


class StructuredJsonFormatter(logging.Formatter):
    """
    Custom logging formatter that outputs structured JSON log lines.
    Automatically injects correlation ID, request path, and user ID
    from the current async context variables.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(),
            "request_path": request_path_var.get(),
            "request_method": request_method_var.get(),
            "user_id": user_id_var.get(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Include exception info if present
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Include any extra metadata attached to the log record
        if hasattr(record, "metadata") and record.metadata:
            log_entry["metadata"] = record.metadata

        return json.dumps(log_entry, default=str)


def configure_structured_logging(level: int = logging.INFO) -> None:
    """
    Configure the root logger to use structured JSON formatting.
    Should be called once during application startup.
    """
    root_logger = logging.getLogger()

    # Avoid duplicate handler registration on repeated calls
    for handler in root_logger.handlers[:]:
        if isinstance(handler.formatter, StructuredJsonFormatter):
            return

    json_handler = logging.StreamHandler()
    json_handler.setFormatter(StructuredJsonFormatter())
    json_handler.setLevel(level)

    root_logger.addHandler(json_handler)
    root_logger.setLevel(level)


# Module-level convenience logger
logger = logging.getLogger("observability.structured_logger")
