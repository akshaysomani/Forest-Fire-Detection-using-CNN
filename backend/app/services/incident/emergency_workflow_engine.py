import logging
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal
from app.models.alert import Alert
from app.models.incident import Incident
from app.services.incident.incident_creator import incident_creator
from app.services.incident.assignment_manager import assignment_manager
from app.services.incident.incident_assignment_service import incident_assignment_service

logger = logging.getLogger("incident.emergency_workflow_engine")


class EmergencyWorkflowEngine:
    async def handle_alert_generated(self, payload: dict) -> None:
        """
        Event subscriber callback triggered when an alert is generated.
        Automatically evaluates and spawns an incident, then auto-dispatches an available team.
        """
        alert_id_str = payload.get("alert_id")
        if not alert_id_str:
            return

        logger.info(f"Emergency workflow engine processing alert: {alert_id_str}")
        alert_id = uuid.UUID(alert_id_str)

        async with SessionLocal() as db:
            try:
                res = await db.execute(select(Alert).where(Alert.id == alert_id, Alert.deleted_at.is_(None)))
                alert = res.scalar_one_or_none()

                if not alert:
                    logger.warning(f"Alert {alert_id} not found for emergency workflow.")
                    return

                # 1. Evaluate rules and auto-spawn incident
                incident = await incident_creator.process_alert(db, alert)
                if incident:
                    # Commit incident creation
                    await db.commit()
                    await db.refresh(incident)

                    # 2. Trigger auto-dispatch
                    await self.auto_dispatch(db, incident)
                    await db.commit()

            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to execute emergency workflow for alert {alert_id}: {e}", exc_info=True)

    async def auto_dispatch(self, db: AsyncSession, incident: Incident) -> bool:
        """
        Runs auto-dispatch logic for a given active incident.
        Finds the best matching response team and dispatches them.
        """
        logger.info(f"Auto-dispatching team for incident {incident.id}")

        # Suggest team
        team = await assignment_manager.suggest_best_team_for_incident(db, incident)
        if not team:
            logger.info(f"No team available for auto-dispatch to incident {incident.id}")
            return False

        try:
            # Create dispatch assignment
            await incident_assignment_service.assign_team(
                db=db, incident_id=incident.id, team_id=team.id, assigned_by=None  # System dispatch
            )
            logger.info(f"Auto-dispatched team '{team.name}' to incident {incident.id}")
            return True
        except Exception as e:
            logger.error(f"Auto-dispatch assignment failed for incident {incident.id}: {e}")
            return False


emergency_workflow_engine = EmergencyWorkflowEngine()
