import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import Incident, ResponseTeam, IncidentAssignment, IncidentEvent, IncidentAuditLog
from app.core.exceptions import ValidationException, EntityNotFoundException
from app.services.incident.incident_service import incident_service
from app.services.incident.incident_lifecycle_service import incident_lifecycle_service

logger = logging.getLogger("incident.incident_assignment_service")


class IncidentAssignmentService:
    async def assign_team(
        self, db: AsyncSession, incident_id: uuid.UUID, team_id: uuid.UUID, assigned_by: Optional[uuid.UUID] = None
    ) -> IncidentAssignment:
        """
        Dispatches a team to an active incident. Creates a pending IncidentAssignment.
        """
        logger.info(f"Assigning team {team_id} to incident {incident_id} by {assigned_by}")

        # 1. Fetch incident
        incident = await incident_service.get_incident_by_id(db, incident_id)
        if incident.status in ["Resolved", "Closed"]:
            raise ValidationException("Cannot assign teams to a resolved or closed incident.")

        # 2. Fetch response team
        team_q = select(ResponseTeam).where(ResponseTeam.id == team_id, ResponseTeam.deleted_at.is_(None))
        team_res = await db.execute(team_q)
        team = team_res.scalar_one_or_none()
        if not team:
            raise EntityNotFoundException("Response team not found.")
        if team.status != "Active":
            raise ValidationException("Response team is not active.")
        if team.current_incident_id is not None:
            raise ValidationException("Response team is already deployed on another active incident.")

        # 3. Check for existing pending/accepted assignment for this team on this incident
        existing_q = select(IncidentAssignment).where(
            and_(
                IncidentAssignment.incident_id == incident_id,
                IncidentAssignment.team_id == team_id,
                IncidentAssignment.status.in_(["Pending", "Accepted"]),
            )
        )
        existing_res = await db.execute(existing_q)
        if existing_res.scalar_one_or_none():
            raise ValidationException("This team is already assigned or pending assignment to this incident.")

        # 4. Create IncidentAssignment
        assignment = IncidentAssignment(
            incident_id=incident_id,
            team_id=team_id,
            assigned_by=assigned_by,
            assigned_at=datetime.now(timezone.utc),
            status="Pending",
        )
        db.add(assignment)
        await db.flush()

        # 5. Log incident event & audit
        event = IncidentEvent(
            incident_id=incident_id,
            event_type="incident_team_assigned",
            payload={
                "team_id": str(team_id),
                "team_name": team.name,
                "assigned_by": str(assigned_by) if assigned_by else "system",
            },
        )
        db.add(event)

        audit = IncidentAuditLog(
            incident_id=incident_id,
            user_id=assigned_by,
            action="incident_assignment_created",
            details={"team_id": str(team_id), "assigned_by": str(assigned_by) if assigned_by else "system"},
        )
        db.add(audit)
        await db.flush()

        logger.info(f"Successfully created assignment {assignment.id} in Pending state.")
        return assignment

    async def accept_assignment(self, db: AsyncSession, assignment_id: uuid.UUID, user_id: uuid.UUID) -> IncidentAssignment:
        """
        Accepts a pending dispatch assignment. Sets team current_incident_id
        and transitions the incident status.
        """
        logger.info(f"Accepting assignment {assignment_id} by user {user_id}")

        # 1. Fetch assignment
        q = select(IncidentAssignment).where(IncidentAssignment.id == assignment_id, IncidentAssignment.deleted_at.is_(None))
        res = await db.execute(q)
        assignment = res.scalar_one_or_none()
        if not assignment:
            raise EntityNotFoundException("Incident assignment not found.")
        if assignment.status != "Pending":
            raise ValidationException(f"Cannot accept assignment in '{assignment.status}' state.")

        # 2. Fetch team & incident
        team_q = select(ResponseTeam).where(ResponseTeam.id == assignment.team_id, ResponseTeam.deleted_at.is_(None))
        team_res = await db.execute(team_q)
        team = team_res.scalar_one_or_none()
        if not team:
            raise EntityNotFoundException("Associated response team not found.")
        if team.current_incident_id is not None:
            raise ValidationException("Team is already deployed on another active incident.")

        incident = await incident_service.get_incident_by_id(db, assignment.incident_id)

        # 3. Transition Incident Status
        target_status = "Assigned"
        if incident.status == "Escalated":
            target_status = "In Progress"

        if incident.status != target_status:
            await incident_lifecycle_service.transition_status(
                db=db,
                incident_id=incident.id,
                new_status=target_status,
                user_id=user_id,
                reason=f"Team '{team.name}' accepted the dispatch assignment.",
            )

        # 4. Update assignment and team status
        assignment.status = "Accepted"
        team.current_incident_id = incident.id
        db.add(assignment)
        db.add(team)

        # 5. Log event & audit
        event = IncidentEvent(
            incident_id=incident.id,
            event_type="incident_assignment_accepted",
            payload={"assignment_id": str(assignment_id), "team_id": str(team.id), "team_name": team.name},
        )
        db.add(event)

        audit = IncidentAuditLog(
            incident_id=incident.id,
            user_id=user_id,
            action="incident_assignment_accepted",
            details={"assignment_id": str(assignment_id), "team_id": str(team.id)},
        )
        db.add(audit)
        await db.flush()

        logger.info(f"Assignment {assignment_id} accepted successfully.")
        return assignment

    async def reject_assignment(
        self, db: AsyncSession, assignment_id: uuid.UUID, user_id: uuid.UUID, reason: str
    ) -> IncidentAssignment:
        """
        Rejects a pending dispatch assignment.
        """
        logger.info(f"Rejecting assignment {assignment_id} by user {user_id}. Reason: {reason}")

        # 1. Fetch assignment
        q = select(IncidentAssignment).where(IncidentAssignment.id == assignment_id, IncidentAssignment.deleted_at.is_(None))
        res = await db.execute(q)
        assignment = res.scalar_one_or_none()
        if not assignment:
            raise EntityNotFoundException("Incident assignment not found.")
        if assignment.status != "Pending":
            raise ValidationException(f"Cannot reject assignment in '{assignment.status}' state.")

        # 2. Update assignment status
        assignment.status = "Rejected"
        db.add(assignment)

        # 3. Log event & audit
        event = IncidentEvent(
            incident_id=assignment.incident_id,
            event_type="incident_assignment_rejected",
            payload={"assignment_id": str(assignment_id), "team_id": str(assignment.team_id), "reason": reason},
        )
        db.add(event)

        audit = IncidentAuditLog(
            incident_id=assignment.incident_id,
            user_id=user_id,
            action="incident_assignment_rejected",
            details={"assignment_id": str(assignment_id), "team_id": str(assignment.team_id), "reason": reason},
        )
        db.add(audit)
        await db.flush()

        logger.info(f"Assignment {assignment_id} rejected successfully.")
        return assignment


incident_assignment_service = IncidentAssignmentService()
