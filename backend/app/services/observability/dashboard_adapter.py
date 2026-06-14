"""
Dashboard Adapter - Transforms observability data into visualization-ready formats.

Converts raw metric entries, log statistics, trace summaries, and SLO
compliance data into structured JSON suitable for frontend charting.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("observability.dashboard_adapter")


class DashboardAdapter:
    """
    Transforms observability data into visualization-ready JSON structures
    compatible with common charting libraries.
    """

    def format_metric_timeseries(
        self,
        metrics: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Format metric entries into a time-series structure.
        Returns labels (timestamps) and datasets (values) for line charts.
        """
        labels = []
        values = []

        for metric in metrics:
            timestamp = metric.get("timestamp")
            if hasattr(timestamp, "isoformat"):
                labels.append(timestamp.isoformat())
            else:
                labels.append(str(timestamp))
            values.append(metric.get("value", 0.0))

        return {
            "chart_type": "timeseries",
            "labels": labels,
            "datasets": [{"label": "value", "data": values}],
        }

    def format_log_distribution(
        self,
        log_stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Format log statistics into a distribution chart structure.
        Suitable for pie/donut charts showing log level breakdown.
        """
        distribution = log_stats.get("level_distribution", {})
        return {
            "chart_type": "distribution",
            "labels": list(distribution.keys()),
            "datasets": [{"label": "Log Level Distribution", "data": list(distribution.values())}],
            "total": log_stats.get("total_logs", 0),
        }

    def format_performance_summary(
        self,
        summaries: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Format endpoint performance summaries into a table structure.
        """
        return {
            "chart_type": "table",
            "columns": [
                "endpoint",
                "method",
                "avg_latency_ms",
                "p95_latency_ms",
                "error_rate",
                "throughput_rpm",
                "total_requests",
            ],
            "rows": summaries,
        }

    def format_slo_compliance(
        self,
        slo_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Format SLO compliance data into a gauge/indicator structure.
        Suitable for dashboard gauges and status indicators.
        """
        evaluations = slo_results.get("evaluations", {})
        indicators = []

        for sli_name, evaluation in evaluations.items():
            indicators.append(
                {
                    "name": sli_name,
                    "target": evaluation.get("target_percentage", 0),
                    "actual": evaluation.get("actual_percentage", 0),
                    "compliant": evaluation.get("compliant", False),
                    "error_budget_remaining": evaluation.get("error_budget_remaining", 0),
                }
            )

        return {
            "chart_type": "gauge",
            "indicators": indicators,
            "overall_compliant": slo_results.get("overall_compliant", False),
        }

    def format_availability(
        self,
        uptime_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Format availability data into a status indicator structure."""
        return {
            "chart_type": "status",
            "windows": {
                "5min": uptime_summary.get("last_5_min", 100.0),
                "15min": uptime_summary.get("last_15_min", 100.0),
                "1hour": uptime_summary.get("last_1_hour", 100.0),
                "24hours": uptime_summary.get("last_24_hours", 100.0),
            },
            "total_pings": uptime_summary.get("total_pings", 0),
        }


# Module-level singleton
dashboard_adapter = DashboardAdapter()
