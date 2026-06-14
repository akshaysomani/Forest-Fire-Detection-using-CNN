import logging
import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.gis import Geofence, GISAuditLog
from app.services.gis.boundary_engine import boundary_engine
from app.core.exceptions import EntityNotFoundException, ValidationException

logger = logging.getLogger("gis.geofence_service")


class GeofenceService:
    async def create_geofence(
        self,
        db: AsyncSession,
        name: str,
        type_: str,
        geometry: dict,
        description: Optional[str] = None,
        is_active: bool = True,
        user_id: Optional[uuid.UUID] = None,
    ) -> Geofence:
        """Create a new Geofence (Circular or Polygon)."""
        logger.info(f"Creating geofence: {name} (Type: {type_})")

        if type_ not in ["Circular", "Polygon"]:
            raise ValidationException("Geofence type must be either 'Circular' or 'Polygon'.")

        # Basic geometry format validation
        if type_ == "Circular":
            if "center" not in geometry or "radius" not in geometry:
                raise ValidationException("Circular geometry must contain 'center' [lat, lng] and 'radius' (meters) keys.")
        elif type_ == "Polygon":
            if "coordinates" not in geometry:
                raise ValidationException("Polygon geometry must contain 'coordinates' list.")

        geofence = Geofence(name=name, description=description, type=type_, geometry=geometry, is_active=is_active)
        db.add(geofence)
        await db.flush()

        # Audit log
        audit = GISAuditLog(
            user_id=user_id, action="geofence_created", details={"geofence_id": str(geofence.id), "name": name, "type": type_}
        )
        db.add(audit)
        await db.flush()

        return geofence

    async def get_geofence_by_id(self, db: AsyncSession, geofence_id: uuid.UUID) -> Geofence:
        query = select(Geofence).where(Geofence.id == geofence_id, Geofence.deleted_at.is_(None))
        res = await db.execute(query)
        geofence = res.scalar_one_or_none()
        if not geofence:
            raise EntityNotFoundException("Geofence not found.")
        return geofence

    async def list_geofences(self, db: AsyncSession, limit: int = 100) -> List[Geofence]:
        query = select(Geofence).where(Geofence.deleted_at.is_(None)).limit(limit)
        res = await db.execute(query)
        return list(res.scalars().all())

    async def check_point_breaches(
        self, db: AsyncSession, latitude: float, longitude: float, user_id: Optional[uuid.UUID] = None
    ) -> List[Geofence]:
        """
        Evaluates active coordinates against all active geofences.
        Records a GISAuditLog entry for each breached geofence.
        Returns a list of breached geofences.
        """
        query = select(Geofence).where(and_(Geofence.is_active == True, Geofence.deleted_at.is_(None)))
        res = await db.execute(query)
        geofences = res.scalars().all()

        breached = []
        for gf in geofences:
            geom = gf.geometry
            is_breached = False

            try:
                if gf.type == "Circular":
                    center = geom["center"]  # [lat, lng]
                    radius = geom["radius"]  # meters
                    distance = boundary_engine.haversine_distance(latitude, longitude, center[0], center[1])
                    if distance <= radius:
                        is_breached = True
                elif gf.type == "Polygon":
                    coords = geom["coordinates"]
                    if coords and len(coords) > 0:
                        outer_ring = coords[0]
                        if boundary_engine.is_point_in_polygon(latitude, longitude, outer_ring):
                            is_breached = True

                if is_breached:
                    logger.warning(f"Geofence '{gf.name}' breached at ({latitude}, {longitude})!")
                    breached.append(gf)

                    # Log breach to GIS Audit Logs
                    audit = GISAuditLog(
                        user_id=user_id,
                        action="geofence_breach",
                        details={
                            "geofence_id": str(gf.id),
                            "geofence_name": gf.name,
                            "latitude": latitude,
                            "longitude": longitude,
                        },
                    )
                    db.add(audit)

            except Exception as e:
                logger.error(f"Error checking geofence {gf.id} breach: {str(e)}")

        if breached:
            await db.flush()

        return breached


geofence_service = GeofenceService()
