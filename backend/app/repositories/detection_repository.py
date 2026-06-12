import uuid
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.detection import Detection


class DetectionRepository(BaseRepository[Detection]):
    def __init__(self):
        super().__init__(Detection)

    async def get_by_user(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> Sequence[Detection]:
        """Fetch all detections uploaded by a specific user."""
        query = select(self.model).where(self.model.user_id == user_id)
        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()


detection_repository = DetectionRepository()
