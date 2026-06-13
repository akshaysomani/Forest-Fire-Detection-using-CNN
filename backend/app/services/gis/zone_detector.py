import logging
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.gis import Region, Zone
from app.services.gis.boundary_engine import boundary_engine

logger = logging.getLogger("gis.zone_detector")


class ZoneDetector:
    async def detect_region_for_coordinates(self, db: AsyncSession, latitude: float, longitude: float) -> Optional[Region]:
        """
        Scans all active regions and returns the containing Region (if any)
        where the coordinates fall inside.
        """
        query = select(Region).where(Region.deleted_at.is_(None))
        res = await db.execute(query)
        regions = res.scalars().all()

        for region in regions:
            try:
                boundary = region.boundary
                if not boundary or "coordinates" not in boundary:
                    continue
                
                # Extract exterior ring of GeoJSON Polygon
                coords = boundary["coordinates"]
                if not coords or len(coords) == 0:
                    continue
                
                outer_ring = coords[0]  # First list represents exterior ring
                if boundary_engine.is_point_in_polygon(latitude, longitude, outer_ring):
                    logger.info(f"Point ({latitude}, {longitude}) detected inside region '{region.name}'")
                    return region
            except Exception as e:
                logger.error(f"Error checking containment in region {region.id}: {str(e)}")

        return None

    async def detect_zone_for_coordinates(self, db: AsyncSession, latitude: float, longitude: float) -> Optional[Zone]:
        """
        Scans all active monitoring zones and returns the containing Zone (if any)
        where the coordinates fall inside.
        """
        query = select(Zone).where(Zone.deleted_at.is_(None))
        res = await db.execute(query)
        zones = res.scalars().all()

        for zone in zones:
            try:
                boundary = zone.boundary
                if not boundary or "coordinates" not in boundary:
                    continue
                
                coords = boundary["coordinates"]
                if not coords or len(coords) == 0:
                    continue
                
                outer_ring = coords[0]
                if boundary_engine.is_point_in_polygon(latitude, longitude, outer_ring):
                    logger.info(f"Point ({latitude}, {longitude}) detected inside zone '{zone.name}' (Risk: {zone.risk_level})")
                    return zone
            except Exception as e:
                logger.error(f"Error checking containment in zone {zone.id}: {str(e)}")

        return None


zone_detector = ZoneDetector()
