"""
Metrics Registry - In-memory counter and gauge storage for high-frequency metric tracking.

Provides thread-safe, lock-free counters and gauges that avoid database write overhead
for every metric sample. Designed to be periodically flushed to database storage.
"""
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

logger = logging.getLogger("observability.metrics_registry")


class MetricsRegistry:
    """
    In-memory registry for application counters and gauge metrics.
    Avoids database writes for every single metric increment.
    Flush snapshots periodically to the MetricsService for persistence.
    """

    def __init__(self):
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._labels: Dict[str, Dict[str, str]] = {}
        self._lock = threading.Lock()

    def increment(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric by a given value."""
        with self._lock:
            self._counters[name] = self._counters.get(name, 0.0) + value
            if labels:
                self._labels[name] = labels

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric to a specific value."""
        with self._lock:
            self._gauges[name] = value
            if labels:
                self._labels[name] = labels

    def get_counter(self, name: str) -> float:
        """Get the current value of a counter."""
        with self._lock:
            return self._counters.get(name, 0.0)

    def get_gauge(self, name: str) -> float:
        """Get the current value of a gauge."""
        with self._lock:
            return self._gauges.get(name, 0.0)

    def get_all_counters(self) -> Dict[str, float]:
        """Return a snapshot of all counter values."""
        with self._lock:
            return dict(self._counters)

    def get_all_gauges(self) -> Dict[str, float]:
        """Return a snapshot of all gauge values."""
        with self._lock:
            return dict(self._gauges)

    def get_snapshot(self) -> List[Dict[str, Any]]:
        """
        Returns a list of all metric samples for database flushing.
        Each entry includes name, value, type, labels, and timestamp.
        """
        now = datetime.now(timezone.utc)
        snapshot = []

        with self._lock:
            for name, value in self._counters.items():
                snapshot.append({
                    "name": name,
                    "value": value,
                    "type": "counter",
                    "labels_json": self._labels.get(name),
                    "timestamp": now,
                })

            for name, value in self._gauges.items():
                snapshot.append({
                    "name": name,
                    "value": value,
                    "type": "gauge",
                    "labels_json": self._labels.get(name),
                    "timestamp": now,
                })

        return snapshot

    def reset_counters(self) -> None:
        """Reset all counters to zero after a flush."""
        with self._lock:
            self._counters.clear()

    def reset_all(self) -> None:
        """Reset all metrics (counters and gauges)."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._labels.clear()


# Module-level singleton
metrics_registry = MetricsRegistry()
