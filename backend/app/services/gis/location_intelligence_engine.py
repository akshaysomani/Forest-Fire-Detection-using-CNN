import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.gis.location_validator import location_validator
from app.services.gis.zone_detector import zone_detector
from app.services.gis.geofence_service import geofence_service
from app.services.gis.location_service import location_service

logger = logging.getLogger("gis.location_intelligence_engine")


class LocationIntelligenceEngine:
    async def get_coordinates_intelligence(self, db: AsyncSession, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Analyzes point coordinates to gather complete spatial intelligence:
        - Resolves address via reverse geocoding
        - Intersects coordinates with administrative regions and monitoring zones
        - Scans for active geofence breaches
        """
        logger.info(f"Gathering location intelligence for Lat: {latitude}, Lng: {longitude}")

        # 1. Validate coordinates
        location_validator.validate_coordinates(latitude, longitude)

        # 2. Resolve Address
        address = location_service.reverse_geocode(latitude, longitude)

        # 3. Intersect Region
        region = await zone_detector.detect_region_for_coordinates(db, latitude, longitude)
        region_name = region.name if region else None
        region_code = region.code if region else None

        # 4. Intersect Zone & Risk Level
        zone = await zone_detector.detect_zone_for_coordinates(db, latitude, longitude)
        zone_name = zone.name if zone else None
        zone_risk_level = zone.risk_level if zone else "Low"

        # 5. Check Geofence breaches
        breached_gfs = await geofence_service.check_point_breaches(db, latitude, longitude)
        breached_names = [gf.name for gf in breached_gfs]

        return {
            "latitude": latitude,
            "longitude": longitude,
            "address": address,
            "region": region_name,
            "region_code": region_code,
            "zone": zone_name,
            "zone_risk_level": zone_risk_level,
            "breached_geofences": breached_names,
            "is_breached": len(breached_names) > 0,
        }


location_intelligence_engine = LocationIntelligenceEngine()
