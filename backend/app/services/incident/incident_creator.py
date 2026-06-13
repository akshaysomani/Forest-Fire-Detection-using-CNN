import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.alert import Alert
from app.models.incident import Incident, IncidentEvent, IncidentAuditLog, IncidentStatusHistory
from app.services.incident.incident_rules_engine import incident_rules_engine

logger = logging.getLogger("incident.incident_creator")


class IncidentCreator:
    async def process_alert(self, db: AsyncSession, alert: Alert) -> Optional[Incident]:
        """
        Evaluate an alert. If it meets auto-spawning rules, create a new incident record,
        set up event logs, and record status history.
        """
        # 1. Evaluate rules
        should_spawn = incident_rules_engine.should_create_incident(alert.severity)
        if not should_spawn:
            logger.debug(f"Alert {alert.id} severity '{alert.severity}' does not trigger auto incident.")
            return None

        logger.info(f"Auto-spawning incident for Alert {alert.id} ({alert.severity})")

        # 2. Pre-load detection to extract coordinates if present
        latitude = None
        longitude = None
        if alert.detection_id:
            # Query detection details
            from app.models.detection import Detection
            res = await db.execute(select(Detection).where(Detection.id == alert.detection_id))
            det = res.scalar_one_or_none()
            if det:
                latitude = det.latitude
                longitude = det.longitude

        # 3. Create Incident
        incident = Incident(
            alert_id=alert.id,
            title=f"Emergency: Auto-Spurned Fire Warning [{alert.severity}]",
            description=alert.message,
            status="Open",
            severity=alert.severity,
            latitude=latitude,
            longitude=longitude
        )
        db.add(incident)
        await db.flush()  # Populates incident.id

        # 4. Insert initial status history
        history = IncidentStatusHistory(
            incident_id=incident.id,
            old_status="None",
            new_status="Open",
            transition_reason=f"System automatically created incident from Alert ID: {alert.id}."
        )
        db.add(history)

        # 5. Insert IncidentEvent log
        event = IncidentEvent(
            incident_id=incident.id,
            event_type="incident_auto_created",
            payload={
                "alert_id": str(alert.id),
                "severity": alert.severity,
                "latitude": latitude,
                "longitude": longitude
            }
        )
        db.add(event)

        # 6. Insert IncidentAuditLog
        audit = IncidentAuditLog(
            incident_id=incident.id,
            action="incident_created",
            details={
                "triggered_by_alert": str(alert.id),
                "severity": alert.severity
            }
        )
        db.add(audit)
        await db.flush()

        logger.info(f"Auto incident created successfully. ID: {incident.id}")
        return incident


incident_creator = IncidentCreator()
