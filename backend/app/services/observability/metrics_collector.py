"""
Metrics Collector - Gathers system infrastructure metrics (CPU, memory, storage)
and application-level statistics for the observability platform.

Integrates with the existing SystemMetrics service for hardware telemetry
and the MetricsRegistry for in-memory application counters.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from app.services.system_metrics import system_metrics
from app.services.observability.metrics_registry import metrics_registry

logger = logging.getLogger("observability.metrics_collector")


class MetricsCollector:
    """
    Collects infrastructure and application-level metric snapshots.
    Designed to be invoked periodically or on-demand for dashboard rendering.
    """

    def collect_infrastructure_metrics(self) -> Dict[str, Any]:
        """
        Gather live infrastructure metrics from the host system.
        Returns CPU, memory, and storage usage data.
        """
        try:
            cpu_usage = system_metrics.get_cpu_usage_percent()
            memory_usage = system_metrics.get_memory_usage()
            storage_usage = system_metrics.get_storage_usage()

            # Update gauges in the in-memory registry
            metrics_registry.set_gauge("system.cpu_usage_percent", cpu_usage)
            metrics_registry.set_gauge(
                "system.memory_usage_percent", memory_usage.get("percentage_used", 0.0)
            )
            metrics_registry.set_gauge(
                "system.storage_usage_percent", storage_usage.get("percentage_used", 0.0)
            )

            return {
                "cpu_usage_percent": cpu_usage,
                "memory": memory_usage,
                "storage": storage_usage,
                "collected_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to collect infrastructure metrics: {e}")
            return {
                "cpu_usage_percent": 0.0,
                "memory": {},
                "storage": {},
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
            }

    def collect_application_metrics(self) -> Dict[str, Any]:
        """
        Collect application-level metrics from the in-memory registry.
        Returns all current counter and gauge values.
        """
        return {
            "counters": metrics_registry.get_all_counters(),
            "gauges": metrics_registry.get_all_gauges(),
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }

    def collect_all(self) -> Dict[str, Any]:
        """Collect both infrastructure and application metrics."""
        return {
            "infrastructure": self.collect_infrastructure_metrics(),
            "application": self.collect_application_metrics(),
        }


# Module-level singleton
metrics_collector = MetricsCollector()
