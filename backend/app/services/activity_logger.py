import logging
import json
import sys
from datetime import datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON payloads."""

    def format(self, record):
        from datetime import timezone

        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        # Inject custom structured activity attributes
        if hasattr(record, "activity_data"):
            log_data["activity"] = record.activity_data
        return json.dumps(log_data)


# Configure a dedicated audit logger
logger = logging.getLogger("audit_logger")
logger.setLevel(logging.INFO)

# Suppress duplicate logs if root logger has handles
logger.propagate = False

# Console stream output formatted as JSON
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(JSONFormatter())
logger.addHandler(console_handler)


class ActivityLogger:
    @staticmethod
    def log_activity(
        user_id: Any = None,
        username: str = None,
        action: str = "",
        resource_type: str = None,
        resource_id: str = None,
        ip_address: str = None,
        details: dict = None,
    ) -> None:
        """Write a structured JSON security audit record to the stdout console logs."""
        activity_data = {
            "user_id": str(user_id) if user_id else None,
            "username": username,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "ip_address": ip_address,
            "details": details or {},
        }
        logger.info(
            f"Audit event: {action} executed on {resource_type or 'None'} {resource_id or 'None'}",
            extra={"activity_data": activity_data},
        )


# Allow typing helper
activity_logger = ActivityLogger()
