import logging
import uuid
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.alert import Alert
from app.services.gis.spatial_integration_manager import spatial_integration_manager
from app.services.gis.geofence_service import geofence_service
from app.services.gis.gis_event_service import gis_event_service

logger = logging.getLogger("gis.location_event_handler")


async def handle_alert_generated_gis(payload: dict) -> None:
    """
    Subscribes to 'alert_generated' events.
    Resolves the coordinates, maps the alert location, and performs geofencing breach checks.
    """
    alert_id_str = payload.get("alert_id")
    if not alert_id_str:
        return

    logger.info(f"GIS handler processing alert_generated event for Alert: {alert_id_str}")
    alert_id = uuid.UUID(alert_id_str)

    async with SessionLocal() as db:
        try:
            # Query alert and join detection to extract coordinates
            from app.models.detection import Detection
            
            res = await db.execute(select(Alert).where(Alert.id == alert_id, Alert.deleted_at.is_(None)))
            alert = res.scalar_one_or_none()

            if not alert or not alert.detection_id:
                logger.debug(f"Alert {alert_id} not found or has no detection link. Skipping GIS.")
                return

            det_res = await db.execute(select(Detection).where(Detection.id == alert.detection_id))
            detection = det_res.scalar_one_or_none()

            if not detection or detection.latitude is None or detection.longitude is None:
                logger.debug(f"Detection link missing or has no coordinate coordinates. Skipping GIS.")
                return

            latitude = detection.latitude
            longitude = detection.longitude

            # 1. Map alert to location record
            await spatial_integration_manager.process_new_fire_coordinates(db, alert.id, latitude, longitude)

            # 2. Perform geofencing checks
            breached_gfs = await geofence_service.check_point_breaches(db, latitude, longitude)
            for gf in breached_gfs:
                # Publish breach to Event Bus
                await gis_event_service.publish_geofence_breach(
                    geofence_id=str(gf.id),
                    geofence_name=gf.name,
                    latitude=latitude,
                    longitude=longitude
                )

            await db.commit()
            logger.info(f"Successfully processed GIS event handler for alert {alert_id}")

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to execute GIS event handler for alert {alert_id}: {e}", exc_info=True)


async def handle_geofence_breach_event(payload: dict) -> None:
    """
    Subscriber callback triggered when a geofence is breached.
    Can trigger notifications to local rangers or dispatch center.
    """
    name = payload.get("geofence_name")
    lat = payload.get("latitude")
    lng = payload.get("longitude")
    logger.warning(f"CRITICAL GIS EVENT: Geofence '{name}' breached at ({lat}, {lng})! Enforce immediate safety warnings.")
