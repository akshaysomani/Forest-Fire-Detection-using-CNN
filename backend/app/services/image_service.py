import uuid
from datetime import datetime
from typing import Sequence, Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundException, ValidationException
from app.models.image import (
    Image,
    ImageMetadata,
    ImageVersion,
    ImageStorageLocation,
    ImageAccessLog,
    ImageAuditLog,
)
from app.repositories.image_repository import (
    image_repository,
    image_metadata_repository,
    image_version_repository,
    image_storage_location_repository,
    image_access_log_repository,
    image_audit_log_repository,
)


class ImageService:
    async def create_image(
        self,
        db: AsyncSession,
        filename: str,
        original_filename: str,
        size_bytes: int,
        md5_hash: str,
        owner_id: uuid.UUID,
        upload_source: str,
        mime_type: str | None = None,
    ) -> Image:
        # Check for duplication globally
        existing = await image_repository.get_by_md5(db, md5_hash)
        if existing:
            raise ValidationException(f"Image with hash '{md5_hash}' already exists (ID: {existing.id}).")

        # Basic source validation
        valid_sources = {"dataset", "manual", "drone", "cctv", "satellite"}
        if upload_source not in valid_sources:
            raise ValidationException(f"Invalid upload source: '{upload_source}'. Valid sources: {valid_sources}")

        db_obj = Image(
            filename=filename,
            original_filename=original_filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            md5_hash=md5_hash,
            owner_id=owner_id,
            upload_source=upload_source,
            status="active",
        )
        db.add(db_obj)
        await db.flush()

        await self.log_audit(db, db_obj.id, owner_id, "create", {"filename": filename, "source": upload_source})
        return db_obj

    async def get_image(self, db: AsyncSession, id: uuid.UUID) -> Image:
        image = await image_repository.get_by_id_with_relations(db, id)
        if not image:
            raise EntityNotFoundException(f"Image with ID {id} not found.")
        return image

    async def list_images(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        owner_id: uuid.UUID | None = None,
        upload_source: str | None = None,
        status: str | None = None,
        search_query: str | None = None,
    ) -> Sequence[Image]:
        return await image_repository.list_images(db, skip, limit, owner_id, upload_source, status, search_query)

    async def count_images(
        self,
        db: AsyncSession,
        owner_id: uuid.UUID | None = None,
        upload_source: str | None = None,
        status: str | None = None,
        search_query: str | None = None,
    ) -> int:
        return await image_repository.count_images(db, owner_id, upload_source, status, search_query)

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
    ) -> Sequence[Image]:
        return await image_repository.advanced_search(
            db=db,
            skip=skip,
            limit=limit,
            min_width=min_width,
            max_width=max_width,
            min_height=min_height,
            max_height=max_height,
            min_latitude=min_latitude,
            max_latitude=max_latitude,
            min_longitude=min_longitude,
            max_longitude=max_longitude,
            start_date=start_date,
            end_date=end_date,
            camera_model=camera_model,
            upload_source=upload_source,
            status=status,
        )

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
    ) -> int:
        return await image_repository.count_advanced_search(
            db=db,
            min_width=min_width,
            max_width=max_width,
            min_height=min_height,
            max_height=max_height,
            min_latitude=min_latitude,
            max_latitude=max_latitude,
            min_longitude=min_longitude,
            max_longitude=max_longitude,
            start_date=start_date,
            end_date=end_date,
            camera_model=camera_model,
            upload_source=upload_source,
            status=status,
        )

    async def delete_image(self, db: AsyncSession, id: uuid.UUID, user_id: uuid.UUID) -> bool:
        # Soft delete
        image = await self.get_image(db, id)
        await image_repository.soft_delete(db, id)
        await self.log_audit(db, id, user_id, "soft_delete", {"filename": image.filename})
        return True

    async def get_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        return await image_repository.get_statistics(db)

    # Secondary entities management
    async def add_or_update_metadata(
        self,
        db: AsyncSession,
        image_id: uuid.UUID,
        width: int,
        height: int,
        exif_data: dict | None = None,
        gps_latitude: float | None = None,
        gps_longitude: float | None = None,
        captured_at: datetime | None = None,
        camera_make: str | None = None,
        camera_model: str | None = None,
        extra_metadata: dict | None = None,
    ) -> ImageMetadata:
        metadata = await image_metadata_repository.get_by_image_id(db, image_id)
        if metadata:
            metadata.width = width
            metadata.height = height
            metadata.exif_data = exif_data
            metadata.gps_latitude = gps_latitude
            metadata.gps_longitude = gps_longitude
            metadata.captured_at = captured_at
            metadata.camera_make = camera_make
            metadata.camera_model = camera_model
            metadata.extra_metadata = extra_metadata
            db.add(metadata)
        else:
            metadata = ImageMetadata(
                image_id=image_id,
                width=width,
                height=height,
                exif_data=exif_data,
                gps_latitude=gps_latitude,
                gps_longitude=gps_longitude,
                captured_at=captured_at,
                camera_make=camera_make,
                camera_model=camera_model,
                extra_metadata=extra_metadata,
            )
            db.add(metadata)

        await db.flush()
        return metadata

    async def add_version(
        self,
        db: AsyncSession,
        image_id: uuid.UUID,
        version_number: int,
        purpose: str,
        file_path: str,
        size_bytes: int,
        md5_hash: str,
    ) -> ImageVersion:
        version = ImageVersion(
            image_id=image_id,
            version_number=version_number,
            purpose=purpose,
            file_path=file_path,
            size_bytes=size_bytes,
            md5_hash=md5_hash,
        )
        db.add(version)
        await db.flush()
        return version

    async def add_storage_location(
        self,
        db: AsyncSession,
        image_id: uuid.UUID,
        version_id: uuid.UUID | None,
        provider: str,
        bucket_or_container: str,
        file_key_or_path: str,
        is_primary: bool = False,
    ) -> ImageStorageLocation:
        # If is_primary=True, deactivate other primary markers for the same image
        if is_primary:
            locations = await image_storage_location_repository.list_locations(db, image_id)
            for loc in locations:
                if loc.is_primary:
                    loc.is_primary = False
                    db.add(loc)

        location = ImageStorageLocation(
            image_id=image_id,
            image_version_id=version_id,
            provider=provider,
            bucket_or_container=bucket_or_container,
            file_key_or_path=file_key_or_path,
            is_primary=is_primary,
        )
        db.add(location)
        await db.flush()
        return location

    async def log_access(
        self,
        db: AsyncSession,
        image_id: uuid.UUID,
        user_id: uuid.UUID | None,
        access_type: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ImageAccessLog:
        # Import timezone locally if not imported globally
        from datetime import timezone

        log = ImageAccessLog(
            image_id=image_id,
            user_id=user_id,
            accessed_at=datetime.now(timezone.utc),
            access_type=access_type,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(log)
        await db.flush()
        return log

    async def log_audit(
        self, db: AsyncSession, image_id: uuid.UUID, user_id: uuid.UUID | None, action: str, changes: dict | None = None
    ) -> ImageAuditLog:
        log = ImageAuditLog(image_id=image_id, user_id=user_id, action=action, changes=changes)
        db.add(log)
        await db.flush()
        return log


image_service = ImageService()
