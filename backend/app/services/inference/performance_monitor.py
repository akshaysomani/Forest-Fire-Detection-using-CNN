import logging
from typing import Dict, Any, List

logger = logging.getLogger("inference.performance_monitor")


class PerformanceMonitor:
    def __init__(self):
        # Store raw history lists for analysis
        self._latencies: List[Dict[str, float]] = []

    def record_latencies(self, preprocessing: float, transformation: float, forward_pass: float, database_save: float) -> None:
        """
        Record stage latencies in seconds.
        """
        total = preprocessing + transformation + forward_pass + database_save
        record = {
            "preprocessing": preprocessing,
            "transformation": transformation,
            "forward_pass": forward_pass,
            "database_save": database_save,
            "total": total,
        }
        self._latencies.append(record)

        # Keep history capped at 1000 items to avoid RAM growth
        if len(self._latencies) > 1000:
            self._latencies.pop(0)

        logger.debug(
            f"Latency Record: total={total*1000:.2f}ms "
            f"(prep={preprocessing*1000:.2f}ms, "
            f"trans={transformation*1000:.2f}ms, "
            f"forward={forward_pass*1000:.2f}ms, "
            f"db={database_save*1000:.2f}ms)"
        )

    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """
        Calculate average latency across all processed steps.
        """
        if not self._latencies:
            return {
                "avg_total_ms": 0.0,
                "avg_preprocessing_ms": 0.0,
                "avg_transformation_ms": 0.0,
                "avg_forward_pass_ms": 0.0,
                "avg_database_save_ms": 0.0,
                "sample_count": 0,
            }

        count = len(self._latencies)
        avg_total = sum(x["total"] for x in self._latencies) / count
        avg_prep = sum(x["preprocessing"] for x in self._latencies) / count
        avg_trans = sum(x["transformation"] for x in self._latencies) / count
        avg_forward = sum(x["forward_pass"] for x in self._latencies) / count
        avg_db = sum(x["database_save"] for x in self._latencies) / count

        return {
            "avg_total_ms": avg_total * 1000.0,
            "avg_preprocessing_ms": avg_prep * 1000.0,
            "avg_transformation_ms": avg_trans * 1000.0,
            "avg_forward_pass_ms": avg_forward * 1000.0,
            "avg_database_save_ms": avg_db * 1000.0,
            "sample_count": count,
        }


performance_monitor = PerformanceMonitor()
