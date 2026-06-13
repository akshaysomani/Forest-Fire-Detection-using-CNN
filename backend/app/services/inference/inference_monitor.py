import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger("inference.monitor")


class InferenceMonitor:
    def __init__(self):
        self._total_requests = 0
        self._label_counts: Dict[str, int] = {"fire": 0, "non-fire": 0}
        self._latencies: List[float] = []
        self._errors_count = 0
        self._startup_time = time.time()

    def record_request(self, label: str, latency: float) -> None:
        """Track throughput and runtime characteristics of a single inference transaction."""
        self._total_requests += 1
        if label in self._label_counts:
            self._label_counts[label] += 1
        else:
            self._label_counts[label] = 1
            
        self._latencies.append(latency)
        # Cap list to prevent RAM bloating
        if len(self._latencies) > 1000:
            self._latencies.pop(0)

    def record_error(self) -> None:
        """Track prediction error metrics."""
        self._errors_count += 1

    def get_realtime_metrics(self) -> Dict[str, Any]:
        """Compile live telemetry statistics."""
        avg_latency = (sum(self._latencies) / len(self._latencies)) if self._latencies else 0.0
        uptime = time.time() - self._startup_time
        
        return {
            "uptime_seconds": uptime,
            "total_requests": self._total_requests,
            "label_distribution": self._label_counts,
            "average_latency_seconds": avg_latency,
            "error_rate_percentage": (self._errors_count / self._total_requests * 100.0) if self._total_requests > 0 else 0.0,
            "throughput_per_minute": (self._total_requests / (uptime / 60.0)) if uptime > 0 else 0.0
        }


inference_monitor = InferenceMonitor()
