import logging
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import Incident
from app.services.gis.fire_location_service import fire_location_service

logger = logging.getLogger("gis.spatial_integration_manager")


class SpatialIntegrationManager:
    async def process_new_fire_coordinates(
        self,
        db: AsyncSession,
        alert_id: uuid.UUID,
        latitude: float,
        longitude: float
    ) -> None:
        """
        Coordinates fire alert location mapping. If the alert is linked to an
        active incident, also links the incident to that same location coordinate reference.
        """
        logger.info(f"Processing GIS integration for alert {alert_id} at ({latitude}, {longitude})")
        
        # 1. Map alert to location
        await fire_location_service.map_alert_to_location(db, alert_id, latitude, longitude)

        # 2. Check if there is a linked incident
        inc_q = select(Incident).where(Incident.alert_id == alert_id, Incident.deleted_at.is_(None))
        res = await db.execute(inc_q)
        incident = res.scalar_one_or_none()

        if incident:
            logger.info(f"Linked incident {incident.id} found for alert {alert_id}. Mapping incident to location.")
            await fire_location_service.map_incident_to_location(db, incident.id, latitude, longitude)


spatial_integration_manager = SpatialIntegrationManager()
