import uuid
from typing import Sequence, Optional
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog


class ActivityRepository:
    async def get_activities(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None
    ) -> Sequence[AuditLog]:
        """Fetch audit log items with optional filtering and pagination."""
        from sqlalchemy.orm import selectinload
        query = select(AuditLog).options(selectinload(AuditLog.user))
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
            
        # Order by newest first
        query = query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_count(
        self,
        db: AsyncSession,
        user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None
    ) -> int:
        """Get total count of matching audit log items."""
        query = select(func.count(AuditLog.id))
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
            
        result = await db.execute(query)
        return result.scalar_one()


activity_repository = ActivityRepository()
