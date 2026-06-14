import logging
import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.gis import Zone, GISAuditLog
from app.core.exceptions import EntityNotFoundException, ValidationException

logger = logging.getLogger("gis.zone_manager")


class ZoneManager:
    async def create_zone(
        self,
        db: AsyncSession,
        name: str,
        code: str,
        region_id: uuid.UUID,
        type_: str,
        boundary: dict,
        risk_level: str = "Low",
        user_id: Optional[uuid.UUID] = None,
    ) -> Zone:
        """Create a new monitoring zone or protected area within a region."""
        logger.info(f"Creating zone: {name} (Code: {code}, Region: {region_id})")

        # Validate code uniqueness
        dup_q = select(Zone).where(Zone.code == code, Zone.deleted_at.is_(None))
        res_dup = await db.execute(dup_q)
        if res_dup.scalar_one_or_none():
            raise ValidationException(f"Zone code '{code}' is already registered.")

        # Validate GeoJSON boundary coordinates format
        if not boundary or "coordinates" not in boundary:
            raise ValidationException("Zone boundary must contain a valid GeoJSON coordinates dictionary.")

        zone = Zone(name=name, code=code, region_id=region_id, type=type_, boundary=boundary, risk_level=risk_level)
        db.add(zone)
        await db.flush()

        # Audit log
        audit = GISAuditLog(
            user_id=user_id,
            action="zone_created",
            details={"zone_id": str(zone.id), "name": name, "code": code, "region_id": str(region_id)},
        )
        db.add(audit)
        await db.flush()

        return zone

    async def get_zone_by_id(self, db: AsyncSession, zone_id: uuid.UUID) -> Zone:
        query = select(Zone).where(Zone.id == zone_id, Zone.deleted_at.is_(None))
        res = await db.execute(query)
        zone = res.scalar_one_or_none()
        if not zone:
            raise EntityNotFoundException("Zone not found.")
        return zone

    async def list_zones(self, db: AsyncSession, limit: int = 100) -> List[Zone]:
        query = select(Zone).where(Zone.deleted_at.is_(None)).limit(limit)
        res = await db.execute(query)
        return list(res.scalars().all())


zone_manager = ZoneManager()
