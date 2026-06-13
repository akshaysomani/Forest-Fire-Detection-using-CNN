import logging
from typing import Dict

logger = logging.getLogger("gis.gis_monitor")


class GISMonitor:
    def __init__(self):
        self._counters: Dict[str, int] = {
            "spatial_queries": 0,
            "geofence_checks": 0,
            "geofence_breaches": 0,
            "location_resolutions": 0,
            "gis_errors": 0
        }

    def increment(self, name: str, value: int = 1):
        if name in self._counters:
            self._counters[name] += value
        else:
            self._counters[name] = value
        logger.debug(f"GIS monitor counter '{name}' updated to {self._counters[name]}")

    def get_in_memory_metrics(self) -> Dict[str, int]:
        return self._counters.copy()


gis_monitor = GISMonitor()
