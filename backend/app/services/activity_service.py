import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog
from app.repositories.activity_repository import activity_repository
from app.services.activity_logger import activity_logger


class ActivityService:
    async def track_activity(
        self,
        db: AsyncSession,
        action: str,
        user_id: Optional[uuid.UUID] = None,
        username: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> AuditLog:
        """
        Record a user or system activity.
        Persists to database audit_logs table and formats a structured JSON console log.
        """
        # Resolve username for logging context if needed
        if user_id and not username:
            from app.repositories.user_repository import user_repository

            user = await user_repository.get_by_id(db, user_id)
            if user:
                username = user.username

        # Write to Database
        audit_rec = AuditLog(
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )
        db.add(audit_rec)
        await db.flush()

        # Write to JSON console logs for external collectors
        activity_logger.log_activity(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            details=details,
        )

        return audit_rec

    async def get_recent_activities(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> List[AuditLog]:
        """Fetch paginated lists of audit log records."""
        return await activity_repository.get_activities(db, skip, limit, user_id, action, resource_type)

    async def get_activity_count(
        self,
        db: AsyncSession,
        user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> int:
        """Get the count of audit logs matching filters."""
        return await activity_repository.get_count(db, user_id, action, resource_type)


activity_service = ActivityService()
