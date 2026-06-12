import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.dataset import DatasetLabel


class LabelRepository(BaseRepository[DatasetLabel]):
    def __init__(self):
        super().__init__(DatasetLabel)

    async def get_by_name(self, db: AsyncSession, name: str, include_deleted: bool = False) -> DatasetLabel | None:
        query = select(DatasetLabel).where(DatasetLabel.name == name)
        if not include_deleted:
            query = query.where(DatasetLabel.deleted_at.is_(None))
        result = await db.execute(query)
        return result.scalar_one_or_none()


label_repository = LabelRepository()
