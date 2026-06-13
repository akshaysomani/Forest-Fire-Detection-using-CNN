import logging
from typing import Dict, Any

logger = logging.getLogger("analytics.analytics_monitor")


class AnalyticsMonitor:
    def __init__(self):
        self._report_execution_times: Dict[str, int] = {}
        self._export_failures: int = 0
        self._kpi_calculation_times: Dict[str, int] = {}

    def record_report_time(self, execution_id: str, duration_ms: int) -> None:
        self._report_execution_times[execution_id] = duration_ms
        logger.debug(f"Monitor logged: Report {execution_id} completed in {duration_ms} ms.")

    def record_kpi_time(self, name: str, duration_ms: int) -> None:
        self._kpi_calculation_times[name] = duration_ms

    def record_export_failure(self) -> None:
        self._export_failures += 1

    def get_performance_summary(self) -> Dict[str, Any]:
        avg_report_time = (
            sum(self._report_execution_times.values()) / len(self._report_execution_times)
            if self._report_execution_times
            else 0.0
        )
        return {
            "total_reports_measured": len(self._report_execution_times),
            "average_report_generation_ms": round(avg_report_time, 2),
            "export_failures_count": self._export_failures,
            "kpi_calculation_benchmarks_ms": self._kpi_calculation_times
        }


analytics_monitor = AnalyticsMonitor()
