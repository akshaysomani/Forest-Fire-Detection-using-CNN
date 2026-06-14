import logging
from typing import Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.gis import Location, Region, Zone, Geofence
from app.services.gis.gis_monitor import gis_monitor

logger = logging.getLogger("gis.spatial_observability_service")


class SpatialObservabilityService:
    async def get_gis_observability_report(self, db: AsyncSession) -> Dict[str, Any]:
        """Gathers system-wide GIS metrics, in-memory counters, and active geofences count."""
        logger.info("Compiling spatial observability report...")

        # Query database counts
        loc_count_res = await db.execute(select(func.count(Location.id)).where(Location.deleted_at.is_(None)))
        total_locations = loc_count_res.scalar() or 0

        reg_count_res = await db.execute(select(func.count(Region.id)).where(Region.deleted_at.is_(None)))
        total_regions = reg_count_res.scalar() or 0

        zone_count_res = await db.execute(select(func.count(Zone.id)).where(Zone.deleted_at.is_(None)))
        total_zones = zone_count_res.scalar() or 0

        gf_count_res = await db.execute(select(func.count(Geofence.id)).where(Geofence.deleted_at.is_(None)))
        total_geofences = gf_count_res.scalar() or 0

        # Gather in-memory monitor counters
        in_memory = gis_monitor.get_in_memory_metrics()

        return {
            "registered_locations": total_locations,
            "registered_regions": total_regions,
            "registered_zones": total_zones,
            "registered_geofences": total_geofences,
            "in_memory_counters": in_memory,
        }


spatial_observability_service = SpatialObservabilityService()
