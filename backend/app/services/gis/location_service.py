import logging
import uuid
from typing import Dict, Any, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.gis import Location, GISAuditLog
from app.services.gis.location_validator import location_validator
from app.core.exceptions import EntityNotFoundException, ValidationException

logger = logging.getLogger("gis.location_service")


class LocationService:
    async def create_location(
        self,
        db: AsyncSession,
        name: str,
        latitude: float,
        longitude: float,
        address: Optional[str] = None,
        elevation: Optional[float] = None,
        description: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> Location:
        """Creates a new Location record after validating coordinates."""
        logger.info(f"Creating location: {name} (Lat: {latitude}, Lng: {longitude})")
        
        # Validate coordinates WGS84
        location_validator.validate_coordinates(latitude, longitude)

        # Resolve address if not provided
        if not address:
            address = self.reverse_geocode(latitude, longitude)

        location = Location(
            name=name,
            latitude=latitude,
            longitude=longitude,
            address=address,
            elevation=elevation,
            description=description
        )
        db.add(location)
        await db.flush()

        # Write GIS Audit log
        audit = GISAuditLog(
            user_id=user_id,
            action="location_created",
            details={
                "location_id": str(location.id),
                "name": name,
                "latitude": latitude,
                "longitude": longitude
            }
        )
        db.add(audit)
        await db.flush()

        return location

    def reverse_geocode(self, latitude: float, longitude: float) -> str:
        """
        Mock reverse geocoding service resolving coordinates to a readable address format
        for forestry ranger stations or divisions.
        """
        # Return format based on lat/lng zones
        lat_short = round(latitude, 2)
        lng_short = round(longitude, 2)
        
        if latitude > 30.0 and longitude < -100.0:
            return f"Northwest Ranger Division [Sectors: {lat_short}N, {abs(lng_short)}W]"
        elif latitude > 0.0 and longitude > 70.0:
            return f"Southeast Forestry Division [Sectors: {lat_short}N, {lng_short}E]"
        else:
            return f"Forest Area Range Sector [Lat: {lat_short}, Lng: {lng_short}]"

    async def get_location_by_id(self, db: AsyncSession, location_id: uuid.UUID) -> Location:
        """Retrieves a single location by ID."""
        query = select(Location).where(Location.id == location_id, Location.deleted_at.is_(None))
        res = await db.execute(query)
        location = res.scalar_one_or_none()
        if not location:
            raise EntityNotFoundException("Location not found.")
        return location

    async def list_locations(self, db: AsyncSession, limit: int = 100) -> List[Location]:
        """Lists active locations."""
        query = select(Location).where(Location.deleted_at.is_(None)).limit(limit)
        res = await db.execute(query)
        return list(res.scalars().all())


location_service = LocationService()
