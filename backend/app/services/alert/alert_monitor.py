import logging
from typing import Dict

logger = logging.getLogger("alert.alert_monitor")


class AlertMonitor:
    def __init__(self):
        self._metrics = {
            "alerts_evaluated": 0,
            "alerts_triggered": 0,
            "escalations_triggered": 0,
        }

    def increment_evaluated(self):
        self._metrics["alerts_evaluated"] += 1

    def increment_triggered(self):
        self._metrics["alerts_triggered"] += 1

    def increment_escalation(self):
        self._metrics["escalations_triggered"] += 1

    def get_monitoring_summary(self) -> Dict[str, int]:
        """Return memory counters for runtime tracking."""
        return self._metrics


alert_monitor = AlertMonitor()
