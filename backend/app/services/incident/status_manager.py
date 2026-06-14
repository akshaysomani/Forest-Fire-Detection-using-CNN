import logging
from app.core.exceptions import ValidationException

logger = logging.getLogger("incident.status_manager")


class StatusManager:
    ALLOWED_TRANSITIONS = {
        "Open": {"Acknowledged", "Assigned", "Resolved", "Closed", "Escalated"},
        "Acknowledged": {"Assigned", "In Progress", "Resolved", "Closed", "Escalated"},
        "Assigned": {"In Progress", "Escalated", "Resolved", "Closed"},
        "In Progress": {"Escalated", "Resolved", "Closed"},
        "Escalated": {"In Progress", "Resolved", "Closed"},
        "Resolved": {"Closed"},
        "Closed": set(),  # Terminal state
    }

    @classmethod
    def validate_transition(cls, old_status: str, new_status: str) -> bool:
        """Validates if status transition from old_status to new_status is allowed."""
        if old_status == new_status:
            return True

        allowed = cls.ALLOWED_TRANSITIONS.get(old_status, set())
        is_allowed = new_status in allowed

        logger.debug(f"Validating state transition: {old_status} -> {new_status} (Allowed={allowed}) -> Result={is_allowed}")
        return is_allowed


status_manager = StatusManager()
