import uuid
import logging
from typing import Sequence, Optional, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.alert import Alert, AlertAuditLog

logger = logging.getLogger("alert.alert_repository")


class AlertRepository(BaseRepository[Alert]):
    def __init__(self):
        super().__init__(Alert)

    async def get_alerts_filtered(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_deleted: bool = False,
    ) -> Tuple[Sequence[Alert], int]:
        """
        Retrieves a filtered, paginated list of alerts and the total matching record count.
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

    async def get_alert_with_details(self, db: AsyncSession, alert_id: uuid.UUID) -> Optional[Alert]:
        """
        Retrieves a single alert with preloaded events and notifications to optimize queries.
        """
        query = (
            select(self.model)
            .where(and_(self.model.id == alert_id, self.model.deleted_at.is_(None)))
            .options(selectinload(self.model.events), selectinload(self.model.notifications))
        )
        res = await db.execute(query)
        return res.scalar_one_or_none()

    async def get_audit_history(
        self, db: AsyncSession, skip: int = 0, limit: int = 100, alert_id: Optional[uuid.UUID] = None
    ) -> Tuple[Sequence[AlertAuditLog], int]:
        """
        Fetch paginated audit log entries with filter query and count.
        """
        query = select(AlertAuditLog)
        count_query = select(func.count()).select_from(AlertAuditLog)

        filters = []
        if alert_id:
            filters.append(AlertAuditLog.alert_id == alert_id)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        query = query.order_by(desc(AlertAuditLog.created_at)).offset(skip).limit(limit)

        res = await db.execute(query)
        items = res.scalars().all()

        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        return items, total


alert_repository = AlertRepository()
