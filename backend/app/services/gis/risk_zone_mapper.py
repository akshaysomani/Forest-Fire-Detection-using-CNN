import logging
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.alert import Alert
from app.models.gis import Location, AlertLocation
from app.services.gis.zone_detector import zone_detector
from app.services.gis.boundary_engine import boundary_engine

logger = logging.getLogger("gis.risk_zone_mapper")


class RiskZoneMapper:
    async def classify_risk_zone(self, db: AsyncSession, latitude: float, longitude: float) -> str:
        """
        Classifies risk levels. If the coordinates fall inside an active monitoring zone,
        it defaults to that zone's risk level. If there is an active 'Critical' or 'High'
        severity fire alert within 500 meters of the point, the risk escalates to 'Extreme'.
        """
        # 1. Proximity check to active severe alerts
        query = select(Alert).where(
            and_(Alert.status == "active", Alert.severity.in_(["Critical", "High"]), Alert.deleted_at.is_(None))
        )
        res = await db.execute(query)
        alerts = res.scalars().all()

        for alert in alerts:
            # Check if alert has a mapped location with coordinates
            loc_link_q = select(AlertLocation).where(AlertLocation.alert_id == alert.id)
            loc_link_res = await db.execute(loc_link_q)
            link = loc_link_res.scalar_one_or_none()

            if link:
                # Retrieve location
                loc_q = select(Location).where(Location.id == link.location_id)
                loc_res = await db.execute(loc_q)
                loc = loc_res.scalar_one_or_none()
                if loc:
                    dist = boundary_engine.haversine_distance(latitude, longitude, loc.latitude, loc.longitude)
                    if dist <= 500.0:  # 500 meters active danger zone
                        logger.warning(f"Extreme risk classified. Severe active alert {alert.id} within {dist:.1f}m.")
                        return "Extreme"

        # 2. Containment zone check
        zone = await zone_detector.detect_zone_for_coordinates(db, latitude, longitude)
        if zone:
            return zone.risk_level

        return "Low"


risk_zone_mapper = RiskZoneMapper()
