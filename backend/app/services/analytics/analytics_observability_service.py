import logging
from typing import Dict, Any
from app.services.analytics.analytics_monitor import analytics_monitor
from app.services.analytics.analytics_metrics import analytics_metrics

logger = logging.getLogger("analytics.analytics_observability_service")


class AnalyticsObservabilityService:
    def get_observability_report(self) -> Dict[str, Any]:
        """Aggregate monitor statistics and run counters for live telemetry dashboards."""
        perf = analytics_monitor.get_performance_summary()
        counts = analytics_metrics.get_metrics()
        
        return {
            "health_status": "healthy" if perf["export_failures_count"] < 5 else "degraded",
            "counters": counts,
            "performance": perf
        }


analytics_observability_service = AnalyticsObservabilityService()
