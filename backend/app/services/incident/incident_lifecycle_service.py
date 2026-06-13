import logging
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import Incident, IncidentStatusHistory, IncidentAuditLog
from app.services.incident.status_manager import status_manager
from app.services.incident.workflow_engine import workflow_engine
from app.core.exceptions import ValidationException, EntityNotFoundException
from app.services.incident.incident_service import incident_service

logger = logging.getLogger("incident.incident_lifecycle_service")


class IncidentLifecycleService:
    async def transition_status(
        self,
        db: AsyncSession,
        incident_id: uuid.UUID,
        new_status: str,
        user_id: uuid.UUID,
        reason: Optional[str] = None
    ) -> Incident:
        """
        Transitions an incident's lifecycle state, checking transition validations,
        inserting transition history logs, and triggering workflow side-effects.
        """
        logger.info(f"Initiating status transition for incident {incident_id} to '{new_status}' by user {user_id}")

        # 1. Fetch Incident
        incident = await incident_service.get_incident_by_id(db, incident_id)

        old_status = incident.status

        # 2. Check transition validation
        if not status_manager.validate_transition(old_status, new_status):
            raise ValidationException(
                f"Transition from '{old_status}' to '{new_status}' is not permitted in incident lifecycle."
            )

        if old_status == new_status:
            return incident

        # 3. Apply state transition
        incident.status = new_status
        db.add(incident)

        # 4. Save to status history
        history = IncidentStatusHistory(
            incident_id=incident.id,
            user_id=user_id,
            old_status=old_status,
            new_status=new_status,
            transition_reason=reason
        )
        db.add(history)

        # 5. Coordinate workflow side effects (e.g. release resources)
        await workflow_engine.execute_workflow(db, incident, old_status, new_status)

        # 6. Save audit trail log
        audit = IncidentAuditLog(
            incident_id=incident.id,
            user_id=user_id,
            action="incident_status_changed",
            details={
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason
            }
        )
        db.add(audit)

        await db.flush()
        logger.info(f"Incident {incident_id} successfully transitioned from '{old_status}' to '{new_status}'")
        return incident


incident_lifecycle_service = IncidentLifecycleService()
