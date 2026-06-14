import logging
from typing import Dict, Any

logger = logging.getLogger("alert.alert_rules_service")


class AlertRulesService:
    def __init__(self):
        # Default alert rules
        self._rules = {"min_confidence_threshold": 0.70, "target_labels": ["fire"], "auto_escalation_enabled": True}

    def get_rules(self) -> Dict[str, Any]:
        """Fetch the current active alert rules."""
        return self._rules

    def update_rules(self, rules_update: Dict[str, Any]) -> Dict[str, Any]:
        """Update active rules parameters."""
        self._rules.update(rules_update)
        logger.info(f"Alert rules updated: {self._rules}")
        return self._rules

    def should_raise_alert(self, prediction_label: str, confidence: float) -> bool:
        """Determines if a prediction matches the rules to trigger an alert."""
        target_labels = self._rules.get("target_labels", ["fire"])
        min_confidence = self._rules.get("min_confidence_threshold", 0.70)

        is_target_label = prediction_label.lower() in [label.lower() for label in target_labels]
        is_above_threshold = confidence >= min_confidence

        should_trigger = is_target_label and is_above_threshold
        logger.debug(
            f"Checking rules: label={prediction_label} (target={target_labels}), "
            f"confidence={confidence:.4f} (min={min_confidence:.4f}) -> Trigger={should_trigger}"
        )
        return should_trigger


alert_rules_service = AlertRulesService()
