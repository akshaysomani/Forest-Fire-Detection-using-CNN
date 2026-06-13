import logging
from datetime import datetime, timezone, timedelta
from typing import Dict

logger = logging.getLogger("alert.alert_priority_manager")


class AlertPriorityManager:
    # SLA Response Thresholds in minutes
    SLA_THRESHOLDS: Dict[str, int] = {
        "Critical": 15,
        "High": 30,
        "Medium": 60,
        "Low": 120,
        "Informational": 1440,  # 24 hours
    }

    @classmethod
    def get_sla_minutes(cls, severity: str) -> int:
        """Returns the SLA acknowledgement deadline in minutes for a given severity level."""
        return cls.SLA_THRESHOLDS.get(severity, 60)

    @classmethod
    def is_sla_breached(cls, severity: str, created_at: datetime, acknowledged_at: datetime | None = None) -> bool:
        """Checks if the SLA threshold has been exceeded for an unacknowledged/unresolved alert."""
        if acknowledged_at is not None:
            return False

        sla_minutes = cls.get_sla_minutes(severity)
        # Ensure created_at is timezone aware
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        elapsed = now - created_at
        return elapsed > timedelta(minutes=sla_minutes)

    @classmethod
    def get_escalation_target_role(cls, severity: str) -> str:
        """Determines target user role for escalation based on alert severity."""
        if severity == "Critical":
            return "Super Admin"
        elif severity == "High":
            return "Admin"
        else:
            return "Operator"


alert_priority_manager = AlertPriorityManager()
