import logging
from typing import Dict

logger = logging.getLogger("alert.notification_metrics")


class NotificationMetrics:
    def __init__(self):
        self._dispatch_metrics = {
            "email_sent": 0,
            "email_failed": 0,
            "in_app_sent": 0,
            "in_app_failed": 0,
            "sms_sent": 0,
            "sms_failed": 0,
        }

    def record_dispatch(self, channel: str, success: bool):
        """Record a dispatch event."""
        suffix = "sent" if success else "failed"
        key = f"{channel.lower()}_{suffix}"
        if key in self._dispatch_metrics:
            self._dispatch_metrics[key] += 1
        else:
            self._dispatch_metrics[key] = 1
        logger.debug(f"Recorded notification metric: {key}={self._dispatch_metrics[key]}")

    def get_metrics_summary(self) -> Dict[str, int]:
        return self._dispatch_metrics


notification_metrics = NotificationMetrics()
