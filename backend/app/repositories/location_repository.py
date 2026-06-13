import uuid
import logging
from typing import Sequence, Optional, Tuple
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.gis import Location, Region, Zone, Geofence, GISAuditLog

logger = logging.getLogger("gis.location_repository")


class LocationRepository(BaseRepository[Location]):
    def __init__(self):
        super().__init__(Location)

    async def get_locations_filtered(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        name: Optional[str] = None
    ) -> Tuple[Sequence[Location], int]:
        query = select(self.model).where(self.model.deleted_at.is_(None))
        count_query = select(func.count()).select_from(self.model).where(self.model.deleted_at.is_(None))

        if name:
            query = query.where(self.model.name.ilike(f"%{name}%"))
            count_query = count_query.where(self.model.name.ilike(f"%{name}%"))

        query = query.order_by(desc(self.model.created_at)).offset(skip).limit(limit)

        res = await db.execute(query)
        items = res.scalars().all()

        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        return items, total

    async def get_regions_filtered(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        type_: Optional[str] = None
    ) -> Tuple[Sequence[Region], int]:
        query = select(Region).where(Region.deleted_at.is_(None))
        count_query = select(func.count()).select_from(Region).where(Region.deleted_at.is_(None))

        if type_:
            query = query.where(Region.type == type_)
            count_query = count_query.where(Region.type == type_)

        query = query.order_by(Region.name).offset(skip).limit(limit)

        res = await db.execute(query)
        items = res.scalars().all()

        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        return items, total

    async def get_zones_filtered(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        region_id: Optional[uuid.UUID] = None
    ) -> Tuple[Sequence[Zone], int]:
        query = select(Zone).where(Zone.deleted_at.is_(None))
        count_query = select(func.count()).select_from(Zone).where(Zone.deleted_at.is_(None))

        if region_id:
            query = query.where(Zone.region_id == region_id)
            count_query = count_query.where(Zone.region_id == region_id)

        query = query.order_by(Zone.name).offset(skip).limit(limit)

        res = await db.execute(query)
        items = res.scalars().all()

        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        return items, total

    async def get_geofences_filtered(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> Tuple[Sequence[Geofence], int]:
        query = select(Geofence).where(Geofence.deleted_at.is_(None))
        count_query = select(func.count()).select_from(Geofence).where(Geofence.deleted_at.is_(None))

        if is_active is not None:
            query = query.where(Geofence.is_active == is_active)
            count_query = count_query.where(Geofence.is_active == is_active)

        query = query.order_by(desc(Geofence.created_at)).offset(skip).limit(limit)

        res = await db.execute(query)
        items = res.scalars().all()

        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        return items, total

    async def get_gis_audit_history(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[Sequence[GISAuditLog], int]:
        query = select(GISAuditLog)
        count_query = select(func.count()).select_from(GISAuditLog)

        query = query.order_by(desc(GISAuditLog.created_at)).offset(skip).limit(limit)

        res = await db.execute(query)
        items = res.scalars().all()

        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        return items, total


location_repository = LocationRepository()
