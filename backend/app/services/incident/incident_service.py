import logging
import uuid
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import Incident, IncidentEvent, IncidentAuditLog, IncidentStatusHistory
from app.core.exceptions import EntityNotFoundException, ValidationException

logger = logging.getLogger("incident.incident_service")


class IncidentService:
    async def get_incident_by_id(self, db: AsyncSession, incident_id: uuid.UUID) -> Incident:
        """Retrieve a single incident by ID, raising EntityNotFoundException if missing."""
        query = select(Incident).where(Incident.id == incident_id, Incident.deleted_at.is_(None))
        result = await db.execute(query)
        incident = result.scalar_one_or_none()
        if not incident:
            raise EntityNotFoundException("Incident not found.")
        return incident

    async def create_manual_incident(self, db: AsyncSession, data: Dict[str, Any], user_id: uuid.UUID) -> Incident:
        """
        Manually creates a new incident report from dispatcher inputs.
        """
        logger.info(f"Manually creating incident by user {user_id}")

        # 1. Instantiate Incident
        incident = Incident(
            alert_id=data.get("alert_id"),
            title=data["title"],
            description=data.get("description"),
            status="Open",
            severity=data.get("severity", "Medium"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
        )
        db.add(incident)
        await db.flush()  # Populates incident.id

        # 2. Insert initial status history
        history = IncidentStatusHistory(
            incident_id=incident.id,
            user_id=user_id,
            old_status="None",
            new_status="Open",
            transition_reason=data.get("transition_reason", "Dispatcher manually created incident report."),
        )
        db.add(history)

        # 3. Log event
        event = IncidentEvent(
            incident_id=incident.id,
            event_type="incident_manually_created",
            payload={"created_by": str(user_id), "title": incident.title, "severity": incident.severity},
        )
        db.add(event)

        # 4. Save Audit trail
        audit = IncidentAuditLog(
            incident_id=incident.id,
            user_id=user_id,
            action="incident_created",
            details={"created_by": str(user_id), "severity": incident.severity},
        )
        db.add(audit)
        await db.flush()

        logger.info(f"Manual incident created successfully. ID: {incident.id}")
        return incident


incident_service = IncidentService()
