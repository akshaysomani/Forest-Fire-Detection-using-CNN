"""
Visualization Service - Returns chart data structures for frontend plotting.

Provides high-level methods to generate visualization-ready data
for the observability dashboard, combining metrics, logs, and traces.
"""

import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.observability.metrics_service import metrics_service
from app.services.observability.logging_service import logging_service
from app.services.observability.dashboard_adapter import dashboard_adapter

logger = logging.getLogger("observability.visualization_service")


class VisualizationService:
    """
    Generates visualization-ready data structures for dashboard rendering.
    Combines data from multiple observability services.
    """

    async def get_metrics_chart(
        self,
        db: AsyncSession,
        metric_name: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Generate time-series chart data for a specific metric.
        """
        result = await metrics_service.query_metrics(db=db, name=metric_name, skip=skip, limit=limit)

        items = result.get("items", [])
        chart_data = []
        for item in items:
            chart_data.append(
                {
                    "timestamp": item.timestamp,
                    "value": item.value,
                }
            )

        return dashboard_adapter.format_metric_timeseries(chart_data)

    async def get_log_distribution_chart(
        self,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Generate log level distribution chart data."""
        stats = await logging_service.get_log_statistics(db)
        return dashboard_adapter.format_log_distribution(stats)

    async def get_performance_table(
        self,
        db: AsyncSession,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """Generate endpoint performance summary table data."""
        from app.services.observability.performance_monitor import performance_monitor

        summaries = await performance_monitor.get_endpoint_summary(db, hours=hours)
        return dashboard_adapter.format_performance_summary(summaries)


# Module-level singleton
visualization_service = VisualizationService()
