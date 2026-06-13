import logging
import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.alert import Alert, AlertEvent, AlertAuditLog
from app.services.alert.event_bus import event_bus

logger = logging.getLogger("alert.alert_engine")


class AlertEngine:
    async def trigger_detection_alert(
        self,
        db: AsyncSession,
        detection_id: uuid.UUID,
        severity: str,
        message: str,
        payload: Dict[str, Any]
    ) -> Alert:
        """
        Creates Alert and AlertEvent database models, logs the activity,
        and publishes the generated alert to the async event bus.
        """
        logger.info(f"Triggering alert for detection: {detection_id} with severity: {severity}")

        # 1. Create the Alert record
        alert = Alert(
            detection_id=detection_id,
            severity=severity,
            status="active",
            message=message
        )
        db.add(alert)
        await db.flush()  # Populates alert.id

        # 2. Log the event details in AlertEvent
        alert_event = AlertEvent(
            alert_id=alert.id,
            event_type="fire_prediction",
            payload=payload
        )
        db.add(alert_event)

        # 3. Write record into AlertAuditLog
        audit_log = AlertAuditLog(
            alert_id=alert.id,
            action="alert_generated",
            details={
                "severity": severity,
                "detection_id": str(detection_id),
                "message": message,
                "payload": payload
            }
        )
        db.add(audit_log)
        await db.flush()

        # 4. Publish alert_generated to Event Bus
        # Enqueue the event so notification workers process it asynchronously.
        event_payload = {
            "alert_id": str(alert.id),
            "detection_id": str(detection_id),
            "severity": severity,
            "message": message
        }
        await event_bus.publish("alert_generated", event_payload)
        logger.debug(f"Alert {alert.id} event published to Event Bus.")

        return alert


alert_engine = AlertEngine()
