import logging
import uuid
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.alert import Alert
from app.services.alert.notification_service import notification_service

logger = logging.getLogger("alert.alert_event_handler")


async def handle_alert_generated(payload: dict) -> None:
    """Callback triggered when an alert is generated."""
    alert_id_str = payload.get("alert_id")
    if not alert_id_str:
        return

    logger.info(f"Asynchronously processing generated alert: {alert_id_str}")
    alert_id = uuid.UUID(alert_id_str)

    async with SessionLocal() as db:
        try:
            res = await db.execute(select(Alert).where(Alert.id == alert_id, Alert.deleted_at.is_(None)))
            alert = res.scalar_one_or_none()

            if not alert:
                logger.warning(f"Alert {alert_id} not found for notification generation.")
                return

            await notification_service.send_alert_notifications(db, alert)
            await db.commit()
            logger.info(f"Successfully processed generated alert notifications for {alert_id}")
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to process background notifications for alert {alert_id}: {e}", exc_info=True)


async def handle_alert_escalated(payload: dict) -> None:
    """Callback triggered when an alert status is escalated."""
    alert_id_str = payload.get("alert_id")
    if not alert_id_str:
        return

    logger.info(f"Asynchronously processing escalated alert: {alert_id_str}")
    alert_id = uuid.UUID(alert_id_str)

    async with SessionLocal() as db:
        try:
            res = await db.execute(select(Alert).where(Alert.id == alert_id, Alert.deleted_at.is_(None)))
            alert = res.scalar_one_or_none()

            if not alert:
                logger.warning(f"Alert {alert_id} not found for escalation notifications.")
                return

            # Re-run dispatch (this will message target roles / active preferences)
            await notification_service.send_alert_notifications(db, alert)
            await db.commit()
            logger.info(f"Successfully processed escalation notifications for {alert_id}")
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to process background escalation notifications for alert {alert_id}: {e}", exc_info=True)
