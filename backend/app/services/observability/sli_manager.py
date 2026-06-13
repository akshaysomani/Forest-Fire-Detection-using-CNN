"""
SLI Manager - Manages Service Level Indicator definitions and target thresholds.

Defines the SLI targets for the Forest Fire Detection platform including
API availability, latency thresholds, error budgets, and inference response times.
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger("observability.sli_manager")

# Standard SLI definitions for the platform
DEFAULT_SLI_TARGETS = {
    "api_availability": {
        "name": "API Availability",
        "description": "Percentage of successful API responses (2xx/3xx)",
        "target_percentage": 99.5,
        "measurement": "success_rate",
        "window_days": 30,
    },
    "api_latency_p95": {
        "name": "API Latency P95",
        "description": "95th percentile response time under threshold",
        "target_percentage": 95.0,
        "measurement": "latency_p95_under_500ms",
        "window_days": 7,
    },
    "inference_latency": {
        "name": "Inference Latency",
        "description": "CNN inference responses within acceptable time",
        "target_percentage": 90.0,
        "measurement": "inference_under_2000ms",
        "window_days": 7,
    },
    "error_rate": {
        "name": "Error Rate",
        "description": "Server error rate below threshold",
        "target_percentage": 99.0,
        "measurement": "error_rate_below_1pct",
        "window_days": 30,
    },
}


class SLIManager:
    """
    Manages Service Level Indicator definitions and evaluation criteria.
    Provides methods to retrieve SLI targets and evaluate current compliance.
    """

    def __init__(self):
        self._targets = dict(DEFAULT_SLI_TARGETS)

    def get_all_targets(self) -> Dict[str, Dict[str, Any]]:
        """Return all registered SLI target definitions."""
        return dict(self._targets)

    def get_target(self, sli_name: str) -> Dict[str, Any]:
        """Get a specific SLI target definition."""
        return self._targets.get(sli_name, {})

    def register_target(
        self,
        key: str,
        name: str,
        description: str,
        target_percentage: float,
        measurement: str,
        window_days: int = 30,
    ) -> None:
        """Register a new custom SLI target."""
        self._targets[key] = {
            "name": name,
            "description": description,
            "target_percentage": target_percentage,
            "measurement": measurement,
            "window_days": window_days,
        }
        logger.info(f"Registered SLI target: {name} ({target_percentage}%)")

    def evaluate_compliance(
        self,
        sli_name: str,
        actual_percentage: float,
    ) -> Dict[str, Any]:
        """
        Evaluate whether an actual measurement meets the SLI target.
        Returns compliance status and error budget details.
        """
        target = self._targets.get(sli_name)
        if not target:
            return {"compliant": False, "error": f"Unknown SLI: {sli_name}"}

        target_pct = target["target_percentage"]
        compliant = actual_percentage >= target_pct
        error_budget_total = 100.0 - target_pct
        error_budget_consumed = max(0.0, target_pct - actual_percentage)
        error_budget_remaining = max(0.0, error_budget_total - error_budget_consumed)

        return {
            "sli_name": sli_name,
            "target_percentage": target_pct,
            "actual_percentage": round(actual_percentage, 4),
            "compliant": compliant,
            "error_budget_total": round(error_budget_total, 4),
            "error_budget_consumed": round(error_budget_consumed, 4),
            "error_budget_remaining": round(error_budget_remaining, 4),
            "window_days": target["window_days"],
        }


# Module-level singleton
sli_manager = SLIManager()
