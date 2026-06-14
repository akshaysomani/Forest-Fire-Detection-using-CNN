import logging
import uuid
from typing import Dict, Any, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.gis import Region

logger = logging.getLogger("gis.forest_region_registry")


class ForestRegionRegistry:
    async def get_region_by_code(self, db: AsyncSession, code: str) -> Optional[Region]:
        """Looks up a region by its unique code identifier."""
        query = select(Region).where(Region.code == code, Region.deleted_at.is_(None))
        res = await db.execute(query)
        return res.scalar_one_or_none()

    async def get_administrative_path(self, db: AsyncSession, region_id: uuid.UUID) -> str:
        """
        Retrieves the hierarchical administrative path of a region.
        Example: "Yosemite Division -> Sierra Range -> Sector 4"
        """
        path = []
        current_id = region_id

        # Loop up hierarchy (limit safety depth to 10)
        for _ in range(10):
            if not current_id:
                break
            query = select(Region.name, Region.parent_id).where(Region.id == current_id, Region.deleted_at.is_(None))
            res = await db.execute(query)
            row = res.first()
            if not row:
                break

            name, parent_id = row
            path.append(name)
            current_id = parent_id

        # Reverse to get top-down ordering
        path.reverse()
        return " -> ".join(path)


forest_region_registry = ForestRegionRegistry()
