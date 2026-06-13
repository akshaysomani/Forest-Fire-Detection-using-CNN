import logging
from typing import Dict, Any
from app.services.alert.event_bus import event_bus

logger = logging.getLogger("gis.gis_event_service")


class GISEventService:
    async def publish_geofence_breach(
        self,
        geofence_id: str,
        geofence_name: str,
        latitude: float,
        longitude: float
    ) -> None:
        """Publishes a geofence breach event to the asynchronous Event Bus."""
        logger.info(f"Publishing geofence breach event: {geofence_name}")
        payload = {
            "geofence_id": geofence_id,
            "geofence_name": geofence_name,
            "latitude": latitude,
            "longitude": longitude
        }
        await event_bus.publish("geofence_breached", payload)


gis_event_service = GISEventService()
