import uuid
import logging
from typing import Sequence, Optional, Tuple
from datetime import datetime
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.incident import Incident, IncidentAuditLog

logger = logging.getLogger("incident.incident_repository")


class IncidentRepository(BaseRepository[Incident]):
    def __init__(self):
        super().__init__(Incident)

    async def get_incidents_filtered(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_deleted: bool = False,
    ) -> Tuple[Sequence[Incident], int]:
        """
        Retrieves a filtered, paginated list of incidents and the total matching record count.
        """
        query = select(self.model)
        count_query = select(func.count()).select_from(self.model)

        filters = []
        if not include_deleted:
            filters.append(self.model.deleted_at.is_(None))
        if status:
            filters.append(self.model.status == status)
        if severity:
            filters.append(self.model.severity == severity)
        if start_date:
            filters.append(self.model.created_at >= start_date)
        if end_date:
            filters.append(self.model.created_at <= end_date)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        query = query.order_by(desc(self.model.created_at)).offset(skip).limit(limit)

        result = await db.execute(query)
        items = result.scalars().all()

        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        return items, total

    async def get_incident_with_details(self, db: AsyncSession, incident_id: uuid.UUID) -> Optional[Incident]:
        """
        Retrieves a single incident with preloaded assignments, updates, and status history.
        """
        query = (
            select(self.model)
            .where(and_(self.model.id == incident_id, self.model.deleted_at.is_(None)))
            .options(
                selectinload(self.model.assignments), selectinload(self.model.updates), selectinload(self.model.status_history)
            )
        )
        res = await db.execute(query)
        return res.scalar_one_or_none()

    async def get_audit_history(
        self, db: AsyncSession, skip: int = 0, limit: int = 100, incident_id: Optional[uuid.UUID] = None
    ) -> Tuple[Sequence[IncidentAuditLog], int]:
        """
        Fetch paginated audit log entries for incidents with filter query and count.
        """
        query = select(IncidentAuditLog)
        count_query = select(func.count()).select_from(IncidentAuditLog)

        filters = []
        if incident_id:
            filters.append(IncidentAuditLog.incident_id == incident_id)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        query = query.order_by(desc(IncidentAuditLog.created_at)).offset(skip).limit(limit)

        res = await db.execute(query)
        items = res.scalars().all()

        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        return items, total


incident_repository = IncidentRepository()
