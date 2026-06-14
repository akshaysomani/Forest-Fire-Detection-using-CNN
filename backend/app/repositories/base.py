from datetime import datetime, timezone
from typing import Generic, Type, TypeVar, Any, Sequence
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get_by_id(self, db: AsyncSession, id: Any, include_deleted: bool = False) -> ModelType | None:
        query = select(self.model).where(self.model.id == id)
        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, skip: int = 0, limit: int = 100, include_deleted: bool = False
    ) -> Sequence[ModelType]:
        query = select(self.model)
        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def create(self, db: AsyncSession, obj_in: dict[str, Any]) -> ModelType:
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.flush()
        return db_obj

    async def update(self, db: AsyncSession, db_obj: ModelType, obj_in: dict[str, Any]) -> ModelType:
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        await db.flush()
        return db_obj

    async def delete(self, db: AsyncSession, id: Any) -> bool:
        db_obj = await self.get_by_id(db, id, include_deleted=True)
        if not db_obj:
            return False
        await db.delete(db_obj)
        await db.flush()
        return True

    async def soft_delete(self, db: AsyncSession, id: Any) -> bool:
        db_obj = await self.get_by_id(db, id, include_deleted=False)
        if not db_obj:
            return False
        db_obj.deleted_at = datetime.now(timezone.utc)
        db.add(db_obj)
        await db.flush()
        return True


class BaseAssociationRepository:
    """Helper for complex association operations if needed."""

    pass
