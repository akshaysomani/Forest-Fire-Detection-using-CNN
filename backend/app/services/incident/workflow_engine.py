import logging
import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import Incident, IncidentAssignment, ResponseTeam, IncidentEvent

logger = logging.getLogger("incident.workflow_engine")


class WorkflowEngine:
    async def execute_workflow(self, db: AsyncSession, incident: Incident, old_status: str, new_status: str):
        """
        Coordinates automated workflows, side effects, and state updates across other components
        (e.g., releasing assigned teams upon resolution/closure).
        """
        logger.debug(f"Executing workflow side-effects for transition {old_status} -> {new_status} on incident {incident.id}")

        # 1. If incident is resolved or closed, release response teams
        if new_status in ["Resolved", "Closed"]:
            # Query all active assignments
            assignment_q = select(IncidentAssignment).where(
                IncidentAssignment.incident_id == incident.id,
                IncidentAssignment.status.in_(["Pending", "Accepted"])
            )
            res = await db.execute(assignment_q)
            assignments = res.scalars().all()

            for assignment in assignments:
                assignment.status = "Completed"
                db.add(assignment)

            # Release teams: update current_incident_id to NULL
            team_update_q = (
                update(ResponseTeam)
                .where(ResponseTeam.current_incident_id == incident.id)
                .values(current_incident_id=None)
            )
            await db.execute(team_update_q)

            # Record event
            event = IncidentEvent(
                incident_id=incident.id,
                event_type="workflow_teams_released",
                payload={
                    "status": new_status,
                    "released_assignments_count": len(assignments)
                }
            )
            db.add(event)
            logger.info(f"Released teams and completed active assignments for incident {incident.id}")


workflow_engine = WorkflowEngine()
