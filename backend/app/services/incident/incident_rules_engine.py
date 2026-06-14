import logging
from typing import Dict, Any

logger = logging.getLogger("incident.incident_rules_engine")


class IncidentRulesEngine:
    def __init__(self):
        self._rules = {"auto_spawn_severities": ["Critical", "High"], "restricted_coordinate_zones": False}

    def get_rules(self) -> Dict[str, Any]:
        return self._rules

    def update_rules(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        self._rules.update(updates)
        logger.info(f"Incident rules updated: {self._rules}")
        return self._rules

    def should_create_incident(self, alert_severity: str) -> bool:
        """Determines if an alert should trigger automatic incident creation."""
        auto_severities = self._rules.get("auto_spawn_severities", ["Critical", "High"])
        should_trigger = alert_severity in auto_severities
        logger.debug(f"Rules evaluation: severity={alert_severity} (auto={auto_severities}) -> AutoSpawn={should_trigger}")
        return should_trigger


incident_rules_engine = IncidentRulesEngine()
