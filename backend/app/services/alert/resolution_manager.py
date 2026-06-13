import logging
import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.alert import Alert, AlertAcknowledgement, AlertAuditLog
from app.core.exceptions import EntityNotFoundException, ValidationException

logger = logging.getLogger("alert.resolution_manager")


class ResolutionManager:
    async def resolve_alert(
        self,
        db: AsyncSession,
        alert_id: uuid.UUID,
        user_id: uuid.UUID,
        notes: Optional[str] = None
    ) -> Alert:
        """
        Mark an alert as resolved and record notes about the action/remedial steps.
        """
        logger.info(f"Resolving alert: {alert_id} by user: {user_id}")

        # 1. Fetch Alert
        res = await db.execute(select(Alert).where(Alert.id == alert_id, Alert.deleted_at.is_(None)))
        alert = res.scalar_one_or_none()

        if not alert:
            raise EntityNotFoundException("Alert not found.")

        if alert.status == "resolved":
            raise ValidationException("Alert is already resolved.")

        # 2. Update status
        alert.status = "resolved"
        db.add(alert)

        # 3. Create acknowledgement entry
        ack = AlertAcknowledgement(
            alert_id=alert.id,
            user_id=user_id,
            action="resolve",
            notes=notes
        )
        db.add(ack)

        # 4. Save Audit trail
        audit = AlertAuditLog(
            alert_id=alert.id,
            user_id=user_id,
            action="alert_resolved",
            details={
                "notes": notes
            }
        )
        db.add(audit)

        await db.flush()
        logger.info(f"Alert {alert_id} successfully marked as resolved.")
        return alert


resolution_manager = ResolutionManager()
