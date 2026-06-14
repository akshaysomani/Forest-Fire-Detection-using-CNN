import logging
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.alert import Alert, AlertAcknowledgement, AlertAuditLog
from app.core.exceptions import EntityNotFoundException, ValidationException

logger = logging.getLogger("alert.alert_acknowledgement_service")


class AlertAcknowledgementService:
    async def acknowledge_alert(
        self, db: AsyncSession, alert_id: uuid.UUID, user_id: uuid.UUID, notes: Optional[str] = None
    ) -> Alert:
        """
        Acknowledges an active or escalated alert, logging who acknowledged it and any remarks.
        """
        logger.info(f"Acknowledging alert: {alert_id} by user: {user_id}")

        # 1. Fetch Alert
        query = db.add  # placeholder or direct select
        # Use select to get the alert
        from sqlalchemy import select

        res = await db.execute(select(Alert).where(Alert.id == alert_id, Alert.deleted_at.is_(None)))
        alert = res.scalar_one_or_none()

        if not alert:
            raise EntityNotFoundException("Alert not found.")

        if alert.status in ["resolved", "acknowledged"]:
            raise ValidationException(f"Alert is already in state: {alert.status}")

        # 2. Update Alert Status
        alert.status = "acknowledged"
        db.add(alert)

        # 3. Create AlertAcknowledgement log
        ack = AlertAcknowledgement(alert_id=alert.id, user_id=user_id, action="acknowledge", notes=notes)
        db.add(ack)

        # 4. Save Audit trail
        audit = AlertAuditLog(
            alert_id=alert.id,
            user_id=user_id,
            action="alert_acknowledged",
            details={"previous_status": alert.status, "notes": notes},
        )
        db.add(audit)

        await db.flush()
        logger.info(f"Alert {alert_id} successfully acknowledged.")
        return alert


alert_acknowledgement_service = AlertAcknowledgementService()
