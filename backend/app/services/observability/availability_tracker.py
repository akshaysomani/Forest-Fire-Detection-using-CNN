"""
Availability Tracker - Tracks real-time API availability and uptime percentages.

Provides methods to record ping results and calculate rolling
availability windows for the platform's core services.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from app.services.observability.metrics_registry import metrics_registry

logger = logging.getLogger("observability.availability_tracker")


class AvailabilityTracker:
    """
    Tracks API availability using in-memory ping result history.
    Calculates rolling availability percentages.
    """

    def __init__(self, max_history: int = 1000):
        self._pings: List[Dict[str, Any]] = []
        self._max_history = max_history

    def record_ping(self, success: bool, service: str = "api", latency_ms: float = 0.0) -> None:
        """Record an availability ping result."""
        self._pings.append(
            {
                "timestamp": datetime.now(timezone.utc),
                "success": success,
                "service": service,
                "latency_ms": latency_ms,
            }
        )

        # Trim history
        if len(self._pings) > self._max_history:
            self._pings = self._pings[-self._max_history :]

        # Update gauge
        availability = self.get_availability_percentage()
        metrics_registry.set_gauge("platform.availability_percent", availability)

    def get_availability_percentage(
        self,
        window_minutes: int = 60,
        service: str = None,
    ) -> float:
        """
        Calculate availability percentage over a rolling time window.
        Returns 100.0 if no pings recorded (assume healthy until proven otherwise).
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        relevant = [p for p in self._pings if p["timestamp"] >= cutoff and (service is None or p["service"] == service)]

        if not relevant:
            return 100.0

        successful = sum(1 for p in relevant if p["success"])
        return round((successful / len(relevant)) * 100.0, 2)

    def get_uptime_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive uptime summary across multiple time windows.
        """
        return {
            "last_5_min": self.get_availability_percentage(window_minutes=5),
            "last_15_min": self.get_availability_percentage(window_minutes=15),
            "last_1_hour": self.get_availability_percentage(window_minutes=60),
            "last_24_hours": self.get_availability_percentage(window_minutes=1440),
            "total_pings": len(self._pings),
            "last_ping": self._pings[-1] if self._pings else None,
        }

    def get_recent_pings(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the most recent ping records."""
        return self._pings[-limit:]


# Module-level singleton
availability_tracker = AvailabilityTracker()
