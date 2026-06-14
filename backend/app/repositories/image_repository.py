import uuid
from datetime import datetime
from typing import Sequence, Any, Dict
from sqlalchemy import select, func, and_, desc, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.image import (
    Image,
    ImageMetadata,
    ImageVersion,
    ImageProcessingLog,
    ImageStorageLocation,
    ImageAccessLog,
    ImageAuditLog,
)


class ImageRepository(BaseRepository[Image]):
    def __init__(self):
        super().__init__(Image)

    async def get_by_id_with_relations(self, db: AsyncSession, id: uuid.UUID, include_deleted: bool = False) -> Image | None:
        query = select(Image).where(Image.id == id)
        if not include_deleted:
            query = query.where(Image.deleted_at.is_(None))
        query = query.options(
            selectinload(Image.metadata_relation),
            selectinload(Image.versions).selectinload(ImageVersion.storage_locations),
            selectinload(Image.storage_locations),
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_md5(self, db: AsyncSession, md5_hash: str, include_deleted: bool = False) -> Image | None:
        query = select(Image).where(Image.md5_hash == md5_hash)
        if not include_deleted:
            query = query.where(Image.deleted_at.is_(None))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def list_images(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        owner_id: uuid.UUID | None = None,
        upload_source: str | None = None,
        status: str | None = None,
        search_query: str | None = None,
        include_deleted: bool = False,
    ) -> Sequence[Image]:
        query = select(Image)
        filters = []
        if not include_deleted:
            filters.append(Image.deleted_at.is_(None))
        if owner_id:
            filters.append(Image.owner_id == owner_id)
        if upload_source:
            filters.append(Image.upload_source == upload_source)
        if status:
            filters.append(Image.status == status)
        if search_query:
            filters.append(Image.filename.ilike(f"%{search_query}%") | Image.original_filename.ilike(f"%{search_query}%"))
        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(Image.created_at.desc()).offset(skip).limit(limit)
        query = query.options(
            selectinload(Image.metadata_relation),
            selectinload(Image.versions).selectinload(ImageVersion.storage_locations),
            selectinload(Image.storage_locations),
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def count_images(
        self,
        db: AsyncSession,
        owner_id: uuid.UUID | None = None,
        upload_source: str | None = None,
        status: str | None = None,
        search_query: str | None = None,
        include_deleted: bool = False,
    ) -> int:
        query = select(func.count()).select_from(Image)
        filters = []
        if not include_deleted:
            filters.append(Image.deleted_at.is_(None))
        if owner_id:
            filters.append(Image.owner_id == owner_id)
        if upload_source:
            filters.append(Image.upload_source == upload_source)
        if status:
            filters.append(Image.status == status)
        if search_query:
            filters.append(Image.filename.ilike(f"%{search_query}%") | Image.original_filename.ilike(f"%{search_query}%"))
        if filters:
            query = query.where(and_(*filters))

        result = await db.execute(query)
        return result.scalar() or 0

    async def advanced_search(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        min_width: int | None = None,
        max_width: int | None = None,
        min_height: int | None = None,
        max_height: int | None = None,
        min_latitude: float | None = None,
        max_latitude: float | None = None,
        min_longitude: float | None = None,
        max_longitude: float | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        camera_model: str | None = None,
        upload_source: str | None = None,
        status: str | None = None,
        include_deleted: bool = False,
    ) -> Sequence[Image]:
        query = select(Image).join(ImageMetadata, isouter=True)
        filters = []
        if not include_deleted:
            filters.append(Image.deleted_at.is_(None))
        if upload_source:
            filters.append(Image.upload_source == upload_source)
        if status:
            filters.append(Image.status == status)
        if min_width is not None:
            filters.append(ImageMetadata.width >= min_width)
        if max_width is not None:
            filters.append(ImageMetadata.width <= max_width)
        if min_height is not None:
            filters.append(ImageMetadata.height >= min_height)
        if max_height is not None:
            filters.append(ImageMetadata.height <= max_height)
        if min_latitude is not None:
            filters.append(ImageMetadata.gps_latitude >= min_latitude)
        if max_latitude is not None:
            filters.append(ImageMetadata.gps_latitude <= max_latitude)
        if min_longitude is not None:
            filters.append(ImageMetadata.gps_longitude >= min_longitude)
        if max_longitude is not None:
            filters.append(ImageMetadata.gps_longitude <= max_longitude)
        if start_date:
            filters.append(ImageMetadata.captured_at >= start_date)
        if end_date:
            filters.append(ImageMetadata.captured_at <= end_date)
        if camera_model:
            filters.append(ImageMetadata.camera_model.ilike(f"%{camera_model}%"))

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(Image.created_at.desc()).offset(skip).limit(limit)
        query = query.options(
            selectinload(Image.metadata_relation),
            selectinload(Image.versions).selectinload(ImageVersion.storage_locations),
            selectinload(Image.storage_locations),
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def count_advanced_search(
        self,
        db: AsyncSession,
        min_width: int | None = None,
        max_width: int | None = None,
        min_height: int | None = None,
        max_height: int | None = None,
        min_latitude: float | None = None,
        max_latitude: float | None = None,
        min_longitude: float | None = None,
        max_longitude: float | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        camera_model: str | None = None,
        upload_source: str | None = None,
        status: str | None = None,
        include_deleted: bool = False,
    ) -> int:
        query = select(func.count()).select_from(Image).join(ImageMetadata, isouter=True)
        filters = []
        if not include_deleted:
            filters.append(Image.deleted_at.is_(None))
        if upload_source:
            filters.append(Image.upload_source == upload_source)
        if status:
            filters.append(Image.status == status)
        if min_width is not None:
            filters.append(ImageMetadata.width >= min_width)
        if max_width is not None:
            filters.append(ImageMetadata.width <= max_width)
        if min_height is not None:
            filters.append(ImageMetadata.height >= min_height)
        if max_height is not None:
            filters.append(ImageMetadata.height <= max_height)
        if min_latitude is not None:
            filters.append(ImageMetadata.gps_latitude >= min_latitude)
        if max_latitude is not None:
            filters.append(ImageMetadata.gps_latitude <= max_latitude)
        if min_longitude is not None:
            filters.append(ImageMetadata.gps_longitude >= min_longitude)
        if max_longitude is not None:
            filters.append(ImageMetadata.gps_longitude <= max_longitude)
        if start_date:
            filters.append(ImageMetadata.captured_at >= start_date)
        if end_date:
            filters.append(ImageMetadata.captured_at <= end_date)
        if camera_model:
            filters.append(ImageMetadata.camera_model.ilike(f"%{camera_model}%"))

        if filters:
            query = query.where(and_(*filters))

        result = await db.execute(query)
        return result.scalar() or 0

    async def get_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """Aggregate statistical breakdowns of active stored images."""
        base_filters = Image.deleted_at.is_(None)

        # 1. Total count and size
        summary_query = select(func.count(Image.id), func.sum(Image.size_bytes)).where(base_filters)
        summary_res = await db.execute(summary_query)
        total_count, total_size = summary_res.first()

        # 2. Breakdowns by upload source
        source_query = (
            select(Image.upload_source, func.count(Image.id), func.sum(Image.size_bytes))
            .where(base_filters)
            .group_by(Image.upload_source)
        )
        source_res = await db.execute(source_query)
        source_breakdown = {}
        for source, count, size in source_res.all():
            source_breakdown[source] = {"count": count, "size_bytes": size or 0}

        # 3. Breakdowns by status
        status_query = select(Image.status, func.count(Image.id)).where(base_filters).group_by(Image.status)
        status_res = await db.execute(status_query)
        status_breakdown = {}
        for status, count in status_res.all():
            status_breakdown[status] = count

        return {
            "total_count": total_count or 0,
            "total_size_bytes": total_size or 0,
            "source_breakdown": source_breakdown,
            "status_breakdown": status_breakdown,
        }


class ImageMetadataRepository(BaseRepository[ImageMetadata]):
    def __init__(self):
        super().__init__(ImageMetadata)

    async def get_by_image_id(self, db: AsyncSession, image_id: uuid.UUID) -> ImageMetadata | None:
        query = select(ImageMetadata).where(ImageMetadata.image_id == image_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()


class ImageVersionRepository(BaseRepository[ImageVersion]):
    def __init__(self):
        super().__init__(ImageVersion)

    async def get_by_image_and_purpose(self, db: AsyncSession, image_id: uuid.UUID, purpose: str) -> ImageVersion | None:
        query = (
            select(ImageVersion)
            .where(and_(ImageVersion.image_id == image_id, ImageVersion.purpose == purpose))
            .options(selectinload(ImageVersion.storage_locations))
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def list_versions(self, db: AsyncSession, image_id: uuid.UUID) -> Sequence[ImageVersion]:
        query = select(ImageVersion).where(ImageVersion.image_id == image_id).order_by(ImageVersion.version_number.asc())
        result = await db.execute(query)
        return result.scalars().all()


class ImageProcessingLogRepository(BaseRepository[ImageProcessingLog]):
    def __init__(self):
        super().__init__(ImageProcessingLog)

    async def get_logs_by_image(self, db: AsyncSession, image_id: uuid.UUID) -> Sequence[ImageProcessingLog]:
        query = (
            select(ImageProcessingLog)
            .where(ImageProcessingLog.image_id == image_id)
            .order_by(ImageProcessingLog.started_at.desc())
        )
        result = await db.execute(query)
        return result.scalars().all()


class ImageStorageLocationRepository(BaseRepository[ImageStorageLocation]):
    def __init__(self):
        super().__init__(ImageStorageLocation)

    async def get_primary_location(self, db: AsyncSession, image_id: uuid.UUID) -> ImageStorageLocation | None:
        query = select(ImageStorageLocation).where(
            and_(ImageStorageLocation.image_id == image_id, ImageStorageLocation.is_primary.is_(True))
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def list_locations(self, db: AsyncSession, image_id: uuid.UUID) -> Sequence[ImageStorageLocation]:
        query = select(ImageStorageLocation).where(ImageStorageLocation.image_id == image_id)
        result = await db.execute(query)
        return result.scalars().all()


class ImageAccessLogRepository(BaseRepository[ImageAccessLog]):
    def __init__(self):
        super().__init__(ImageAccessLog)

    async def get_logs_by_image(
        self, db: AsyncSession, image_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[ImageAccessLog]:
        query = (
            select(ImageAccessLog)
            .where(ImageAccessLog.image_id == image_id)
            .order_by(ImageAccessLog.accessed_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()


class ImageAuditLogRepository(BaseRepository[ImageAuditLog]):
    def __init__(self):
        super().__init__(ImageAuditLog)

    async def get_logs_by_image(self, db: AsyncSession, image_id: uuid.UUID) -> Sequence[ImageAuditLog]:
        query = select(ImageAuditLog).where(ImageAuditLog.image_id == image_id).order_by(ImageAuditLog.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()


image_repository = ImageRepository()
image_metadata_repository = ImageMetadataRepository()
image_version_repository = ImageVersionRepository()
image_processing_log_repository = ImageProcessingLogRepository()
image_storage_location_repository = ImageStorageLocationRepository()
image_access_log_repository = ImageAccessLogRepository()
image_audit_log_repository = ImageAuditLogRepository()
