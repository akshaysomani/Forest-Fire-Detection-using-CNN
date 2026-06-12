import uuid
from typing import Sequence, Any
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.dataset import (
    Dataset,
    DatasetCategory,
    DatasetVersion,
    DatasetFile,
    DatasetUploadHistory,
    DatasetAuditLog,
)


class DatasetCategoryRepository(BaseRepository[DatasetCategory]):
    def __init__(self):
        super().__init__(DatasetCategory)

    async def get_by_name(self, db: AsyncSession, name: str, include_deleted: bool = False) -> DatasetCategory | None:
        query = select(DatasetCategory).where(DatasetCategory.name == name)
        if not include_deleted:
            query = query.where(DatasetCategory.deleted_at.is_(None))
        result = await db.execute(query)
        return result.scalar_one_or_none()


class DatasetRepository(BaseRepository[Dataset]):
    def __init__(self):
        super().__init__(Dataset)

    async def get_by_name(self, db: AsyncSession, name: str, include_deleted: bool = False) -> Dataset | None:
        query = select(Dataset).where(Dataset.name == name)
        if not include_deleted:
            query = query.where(Dataset.deleted_at.is_(None))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_relations(self, db: AsyncSession, id: uuid.UUID, include_deleted: bool = False) -> Dataset | None:
        query = select(Dataset).where(Dataset.id == id)
        if not include_deleted:
            query = query.where(Dataset.deleted_at.is_(None))
        query = query.options(
            selectinload(Dataset.category),
            selectinload(Dataset.versions),
            selectinload(Dataset.uploads),
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def list_datasets(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        category_id: uuid.UUID | None = None,
        status: str | None = None,
        search_query: str | None = None,
        user_id: uuid.UUID | None = None,
        include_deleted: bool = False,
    ) -> Sequence[Dataset]:
        query = select(Dataset)
        filters = []
        if not include_deleted:
            filters.append(Dataset.deleted_at.is_(None))
        if category_id:
            filters.append(Dataset.category_id == category_id)
        if status:
            filters.append(Dataset.status == status)
        if user_id:
            filters.append(Dataset.user_id == user_id)
        if search_query:
            filters.append(
                Dataset.name.ilike(f"%{search_query}%")
                | Dataset.description.ilike(f"%{search_query}%")
                | Dataset.tags.ilike(f"%{search_query}%")
            )
        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(Dataset.created_at.desc()).offset(skip).limit(limit)
        query = query.options(selectinload(Dataset.category))
        result = await db.execute(query)
        return result.scalars().all()

    async def count_datasets(
        self,
        db: AsyncSession,
        category_id: uuid.UUID | None = None,
        status: str | None = None,
        search_query: str | None = None,
        user_id: uuid.UUID | None = None,
        include_deleted: bool = False,
    ) -> int:
        query = select(func.count()).select_from(Dataset)
        filters = []
        if not include_deleted:
            filters.append(Dataset.deleted_at.is_(None))
        if category_id:
            filters.append(Dataset.category_id == category_id)
        if status:
            filters.append(Dataset.status == status)
        if user_id:
            filters.append(Dataset.user_id == user_id)
        if search_query:
            filters.append(
                Dataset.name.ilike(f"%{search_query}%")
                | Dataset.description.ilike(f"%{search_query}%")
                | Dataset.tags.ilike(f"%{search_query}%")
            )
        if filters:
            query = query.where(and_(*filters))

        result = await db.execute(query)
        return result.scalar() or 0


class DatasetVersionRepository(BaseRepository[DatasetVersion]):
    def __init__(self):
        super().__init__(DatasetVersion)

    async def get_by_dataset_and_version(
        self, db: AsyncSession, dataset_id: uuid.UUID, version_str: str, include_deleted: bool = False
    ) -> DatasetVersion | None:
        query = select(DatasetVersion).where(
            and_(DatasetVersion.dataset_id == dataset_id, DatasetVersion.version_str == version_str)
        )
        if not include_deleted:
            query = query.where(DatasetVersion.deleted_at.is_(None))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_dataset(
        self, db: AsyncSession, dataset_id: uuid.UUID, include_deleted: bool = False
    ) -> Sequence[DatasetVersion]:
        query = select(DatasetVersion).where(DatasetVersion.dataset_id == dataset_id)
        if not include_deleted:
            query = query.where(DatasetVersion.deleted_at.is_(None))
        query = query.order_by(DatasetVersion.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()


class DatasetFileRepository(BaseRepository[DatasetFile]):
    def __init__(self):
        super().__init__(DatasetFile)

    async def get_by_dataset(
        self, db: AsyncSession, dataset_id: uuid.UUID, skip: int = 0, limit: int = 100, include_deleted: bool = False
    ) -> Sequence[DatasetFile]:
        query = select(DatasetFile).where(DatasetFile.dataset_id == dataset_id)
        if not include_deleted:
            query = query.where(DatasetFile.deleted_at.is_(None))
        query = query.options(selectinload(DatasetFile.label)).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_by_md5(
        self, db: AsyncSession, dataset_id: uuid.UUID, md5_hash: str, include_deleted: bool = False
    ) -> DatasetFile | None:
        query = select(DatasetFile).where(
            and_(DatasetFile.dataset_id == dataset_id, DatasetFile.md5_hash == md5_hash)
        )
        if not include_deleted:
            query = query.where(DatasetFile.deleted_at.is_(None))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def count_by_dataset(self, db: AsyncSession, dataset_id: uuid.UUID, include_deleted: bool = False) -> int:
        query = select(func.count()).select_from(DatasetFile).where(DatasetFile.dataset_id == dataset_id)
        if not include_deleted:
            query = query.where(DatasetFile.deleted_at.is_(None))
        result = await db.execute(query)
        return result.scalar() or 0

    async def get_active_files_by_dataset(self, db: AsyncSession, dataset_id: uuid.UUID) -> Sequence[DatasetFile]:
        """Fetch all files associated with a dataset that are currently active (not snapshotted to a specific version or soft deleted)."""
        query = select(DatasetFile).where(
            and_(
                DatasetFile.dataset_id == dataset_id,
                DatasetFile.deleted_at.is_(None),
            )
        ).options(selectinload(DatasetFile.label))
        result = await db.execute(query)
        return result.scalars().all()


class DatasetUploadHistoryRepository(BaseRepository[DatasetUploadHistory]):
    def __init__(self):
        super().__init__(DatasetUploadHistory)

    async def get_by_dataset(
        self, db: AsyncSession, dataset_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[DatasetUploadHistory]:
        query = (
            select(DatasetUploadHistory)
            .where(DatasetUploadHistory.dataset_id == dataset_id)
            .order_by(DatasetUploadHistory.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()


class DatasetAuditLogRepository(BaseRepository[DatasetAuditLog]):
    def __init__(self):
        super().__init__(DatasetAuditLog)

    async def get_by_dataset(
        self, db: AsyncSession, dataset_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[DatasetAuditLog]:
        query = (
            select(DatasetAuditLog)
            .where(DatasetAuditLog.dataset_id == dataset_id)
            .order_by(DatasetAuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()


# Global Instances
dataset_category_repository = DatasetCategoryRepository()
dataset_repository = DatasetRepository()
dataset_version_repository = DatasetVersionRepository()
dataset_file_repository = DatasetFileRepository()
dataset_upload_history_repository = DatasetUploadHistoryRepository()
dataset_audit_log_repository = DatasetAuditLogRepository()
