import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.security import SecurityEvent
from app.core.exceptions import ValidationException


class SecurityIncidentTracker:
    async def track_threat_incident(self, db: AsyncSession, event_id: uuid.UUID, escalation_reason: str) -> SecurityEvent:
        """Escalate a security event to active threat incident tracking."""
        q = select(SecurityEvent).where(SecurityEvent.id == event_id)
        res = await db.execute(q)
        event = res.scalar_one_or_none()

        if not event:
            raise ValidationException("Security event not found.")

        # Update event metadata to record escalation details
        details = event.details_json or {}
        details["escalation"] = {"escalated_at": datetime.utcnow().isoformat(), "reason": escalation_reason, "status": "OPEN"}
        event.details_json = details
        db.add(event)
        await db.flush()
        return event

    async def get_active_incidents(self, db: AsyncSession) -> List[SecurityEvent]:
        """Fetch open threats and security incidents (severity HIGH/CRITICAL)."""
        q = select(SecurityEvent).where(SecurityEvent.severity.in_(["HIGH", "CRITICAL"]))
        res = await db.execute(q)
        events = res.scalars().all()

        # Filter for unresolved ones in python for json structure simplicity
        active = []
        for e in events:
            details = e.details_json or {}
            # If it's a threat blocked or has open escalation status
            if e.event_type == "THREAT_BLOCKED" or (details.get("escalation", {}).get("status") == "OPEN"):
                active.append(e)
        return active

    async def resolve_incident(
        self, db: AsyncSession, event_id: uuid.UUID, comment: str, resolver_id: Optional[uuid.UUID] = None
    ) -> SecurityEvent:
        """Mark an active security incident as resolved with justification."""
        q = select(SecurityEvent).where(SecurityEvent.id == event_id)
        res = await db.execute(q)
        event = res.scalar_one_or_none()

        if not event:
            raise ValidationException("Security incident not found.")

        details = event.details_json or {}
        details["resolution"] = {
            "resolved_at": datetime.utcnow().isoformat(),
            "resolved_by": str(resolver_id) if resolver_id else "SYSTEM",
            "comment": comment,
        }
        if "escalation" in details:
            details["escalation"]["status"] = "RESOLVED"

        # If it was an IP block, we can unblock the IP if resolved
        if event.event_type == "THREAT_BLOCKED" and event.ip_address:
            from app.services.security.api_security_service import api_security_service

            api_security_service.unblock_ip(event.ip_address)
            details["ip_unblocked"] = True

        event.details_json = details
        db.add(event)
        await db.flush()
        return event


security_incident_tracker = SecurityIncidentTracker()
