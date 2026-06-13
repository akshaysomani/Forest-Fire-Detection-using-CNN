import logging
import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.gis import Region, GISAuditLog
from app.core.exceptions import EntityNotFoundException, ValidationException

logger = logging.getLogger("gis.region_service")


class RegionService:
    async def create_region(
        self,
        db: AsyncSession,
        name: str,
        code: str,
        type_: str,
        boundary: dict,
        parent_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> Region:
        """Create a new administrative Region (e.g. Division, Range)."""
        logger.info(f"Creating region: {name} (Code: {code}, Type: {type_})")

        # Validate code uniqueness
        dup_q = select(Region).where(Region.code == code, Region.deleted_at.is_(None))
        res_dup = await db.execute(dup_q)
        if res_dup.scalar_one_or_none():
            raise ValidationException(f"Region code '{code}' is already registered.")

        # Validate GeoJSON boundary coordinates format
        if not boundary or "coordinates" not in boundary:
            raise ValidationException("Region boundary must contain a valid GeoJSON coordinates dictionary.")

        region = Region(
            name=name,
            code=code,
            type=type_,
            parent_id=parent_id,
            boundary=boundary
        )
        db.add(region)
        await db.flush()

        # Audit log
        audit = GISAuditLog(
            user_id=user_id,
            action="region_created",
            details={
                "region_id": str(region.id),
                "name": name,
                "code": code
            }
        )
        db.add(audit)
        await db.flush()

        return region

    async def get_region_by_id(self, db: AsyncSession, region_id: uuid.UUID) -> Region:
        query = select(Region).where(Region.id == region_id, Region.deleted_at.is_(None))
        res = await db.execute(query)
        region = res.scalar_one_or_none()
        if not region:
            raise EntityNotFoundException("Region not found.")
        return region

    async def list_regions(self, db: AsyncSession, limit: int = 100) -> List[Region]:
        query = select(Region).where(Region.deleted_at.is_(None)).limit(limit)
        res = await db.execute(query)
        return list(res.scalars().all())

    async def seed_default_regions(self, db: AsyncSession) -> None:
        """Seeds default forest administrative regions if not already present."""
        logger.info("Checking default regions seeding...")
        
        default_regions = [
            {
                "name": "Yosemite Forest Division",
                "code": "YOS-DIV",
                "type": "Forest Division",
                "boundary": {
                    "type": "Polygon",
                    "coordinates": [
                        [[37.0, -120.0], [38.0, -120.0], [38.0, -119.0], [37.0, -119.0], [37.0, -120.0]]
                    ]
                }
            },
            {
                "name": "Northwest Forestry Range",
                "code": "NW-RNG",
                "type": "Forest Range",
                "boundary": {
                    "type": "Polygon",
                    "coordinates": [
                        [[40.0, -125.0], [42.0, -125.0], [42.0, -120.0], [40.0, -120.0], [40.0, -125.0]]
                    ]
                }
            }
        ]

        for r in default_regions:
            # Check if region code exists
            check_q = select(Region).where(Region.code == r["code"], Region.deleted_at.is_(None))
            res = await db.execute(check_q)
            if not res.scalar_one_or_none():
                logger.info(f"Seeding default region: {r['name']}")
                region = Region(
                    name=r["name"],
                    code=r["code"],
                    type=r["type"],
                    boundary=r["boundary"]
                )
                db.add(region)
        
        await db.flush()


region_service = RegionService()
