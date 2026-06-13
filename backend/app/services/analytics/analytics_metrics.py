import logging
from typing import Dict, Any

logger = logging.getLogger("analytics.analytics_metrics")


class AnalyticsMetrics:
    def __init__(self):
        self._totals = {
            "reports_generated": 0,
            "pdfs_exported": 0,
            "xlsx_exported": 0,
            "csv_exported": 0,
            "json_exported": 0,
            "scheduled_jobs_run": 0
        }

    def increment(self, metric_name: str, val: int = 1) -> None:
        if metric_name in self._totals:
            self._totals[metric_name] += val
            logger.debug(f"Metric incremented: {metric_name} = {self._totals[metric_name]}")

    def get_metrics(self) -> Dict[str, int]:
        return self._totals


analytics_metrics = AnalyticsMetrics()
