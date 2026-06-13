import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.security import SecurityEvent
from app.services.security.security_audit_logger import security_audit_logger


class SecurityEventService:
    async def log_event(
        self,
        db: AsyncSession,
        event_type: str,
        severity: str,
        description: str,
        user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details_json: Optional[dict] = None
    ) -> SecurityEvent:
        """Create, persist, and format security telemetry event."""
        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            description=description,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details_json=details_json
        )
        db.add(event)
        await db.flush()

        # Emit to SIEM audit log
        security_audit_logger.log_event(
            event_type=event_type,
            severity=severity,
            description=description,
            user_id=str(user_id) if user_id else None,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details_json
        )

        return event

    async def get_events(
        self,
        db: AsyncSession,
        severity: Optional[str] = None,
        event_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[SecurityEvent]:
        """Fetch historical security logs."""
        q = select(SecurityEvent)
        if severity:
            q = q.where(SecurityEvent.severity == severity)
        if event_type:
            q = q.where(SecurityEvent.event_type == event_type)
        
        q = q.order_by(desc(SecurityEvent.timestamp)).offset(skip).limit(limit)
        res = await db.execute(q)
        return list(res.scalars().all())


security_event_service = SecurityEventService()
