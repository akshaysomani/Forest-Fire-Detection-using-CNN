"""
Reliability Alert Service - Dispatches alert notifications on SLO threshold violations.

Monitors SLO compliance evaluations and generates structured alert records
when service reliability falls below acceptable thresholds.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("observability.reliability_alert_service")


class ReliabilityAlertService:
    """
    Manages reliability alerting based on SLO compliance evaluations.
    Generates structured alert records for operations team notification.
    """

    def __init__(self):
        self._alert_history: List[Dict[str, Any]] = []

    def evaluate_and_alert(
        self,
        slo_evaluation: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Check an SLO evaluation result and generate an alert if non-compliant.
        Returns an alert dict if triggered, None otherwise.
        """
        if slo_evaluation.get("compliant", True):
            return None

        alert = {
            "alert_type": "slo_violation",
            "severity": self._determine_severity(slo_evaluation),
            "sli_name": slo_evaluation.get("sli_name", "unknown"),
            "target_percentage": slo_evaluation.get("target_percentage", 0.0),
            "actual_percentage": slo_evaluation.get("actual_percentage", 0.0),
            "error_budget_remaining": slo_evaluation.get("error_budget_remaining", 0.0),
            "message": (
                f"SLO violation: {slo_evaluation.get('sli_name', 'unknown')} "
                f"at {slo_evaluation.get('actual_percentage', 0)}% "
                f"(target: {slo_evaluation.get('target_percentage', 0)}%)"
            ),
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        }

        self._alert_history.append(alert)
        logger.warning(f"Reliability alert triggered: {alert['message']}")
        return alert

    def _determine_severity(self, evaluation: Dict[str, Any]) -> str:
        """Determine alert severity based on error budget consumption."""
        budget_remaining = evaluation.get("error_budget_remaining", 100.0)

        if budget_remaining <= 0:
            return "critical"
        elif budget_remaining < 0.25:
            return "high"
        elif budget_remaining < 0.5:
            return "medium"
        return "low"

    def check_all_slos(
        self,
        slo_results: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Check all SLO evaluation results and return any triggered alerts.
        """
        alerts = []
        evaluations = slo_results.get("evaluations", {})

        for sli_name, evaluation in evaluations.items():
            alert = self.evaluate_and_alert(evaluation)
            if alert:
                alerts.append(alert)

        return alerts

    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent reliability alert history."""
        return self._alert_history[-limit:]

    def clear_history(self) -> None:
        """Clear the in-memory alert history."""
        self._alert_history.clear()


# Module-level singleton
reliability_alert_service = ReliabilityAlertService()
