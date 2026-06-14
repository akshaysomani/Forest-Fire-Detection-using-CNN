import logging
import uuid
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.gis import Location, AlertLocation, IncidentLocation
from app.services.gis.location_service import location_service
from app.services.gis.boundary_engine import boundary_engine

logger = logging.getLogger("gis.fire_location_service")


class FireLocationService:
    async def map_alert_to_location(
        self, db: AsyncSession, alert_id: uuid.UUID, latitude: float, longitude: float
    ) -> AlertLocation:
        """
        Links an alert to a geocoded reference point.
        Checks for an existing location within a 50-meter radius to reuse and prevent duplication.
        """
        logger.info(f"Mapping alert {alert_id} to location (Lat: {latitude}, Lng: {longitude})")
        location = await self._find_or_create_proximity_location(db, latitude, longitude, f"Alert Site: {alert_id}")

        # Check if already linked
        check_q = select(AlertLocation).where(
            and_(AlertLocation.alert_id == alert_id, AlertLocation.location_id == location.id)
        )
        res = await db.execute(check_q)
        alert_link = res.scalar_one_or_none()

        if not alert_link:
            alert_link = AlertLocation(alert_id=alert_id, location_id=location.id)
            db.add(alert_link)
            await db.flush()

        return alert_link

    async def map_incident_to_location(
        self, db: AsyncSession, incident_id: uuid.UUID, latitude: float, longitude: float
    ) -> IncidentLocation:
        """
        Links an incident dispatch to a location.
        Reuses existing locations within 50 meters to avoid redundancy.
        """
        logger.info(f"Mapping incident {incident_id} to location (Lat: {latitude}, Lng: {longitude})")
        location = await self._find_or_create_proximity_location(db, latitude, longitude, f"Incident Site: {incident_id}")

        check_q = select(IncidentLocation).where(
            and_(IncidentLocation.incident_id == incident_id, IncidentLocation.location_id == location.id)
        )
        res = await db.execute(check_q)
        incident_link = res.scalar_one_or_none()

        if not incident_link:
            incident_link = IncidentLocation(incident_id=incident_id, location_id=location.id)
            db.add(incident_link)
            await db.flush()

        return incident_link

    async def _find_or_create_proximity_location(
        self, db: AsyncSession, latitude: float, longitude: float, default_name: str
    ) -> Location:
        """Helper to find an existing location within 50 meters, or create a new one."""
        query = select(Location).where(Location.deleted_at.is_(None))
        res = await db.execute(query)
        locations = res.scalars().all()

        for loc in locations:
            dist = boundary_engine.haversine_distance(latitude, longitude, loc.latitude, loc.longitude)
            if dist <= 50.0:  # 50 meters proximity check
                logger.info(f"Reusing existing location '{loc.name}' (Distance: {dist:.1f}m)")
                return loc

        # Create new Location
        return await location_service.create_location(db=db, name=default_name, latitude=latitude, longitude=longitude)


fire_location_service = FireLocationService()
