import logging
from typing import Dict, Any

logger = logging.getLogger("incident.incident_monitor")


class IncidentMonitor:
    def __init__(self):
        self._counters: Dict[str, int] = {
            "total_incidents_created": 0,
            "total_escalations": 0,
            "scheduler_runs": 0,
            "scheduler_errors": 0,
            "sla_breaches_detected": 0,
        }

    def increment(self, name: str, value: int = 1):
        if name in self._counters:
            self._counters[name] += value
        else:
            self._counters[name] = value
        logger.debug(f"Monitor metric '{name}' incremented by {value}. Total: {self._counters[name]}")

    def get_in_memory_metrics(self) -> Dict[str, int]:
        return self._counters.copy()


incident_monitor = IncidentMonitor()
