import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundException, ValidationException
from app.services.image_service import image_service
from app.services.archive_manager import archive_manager
from app.services.cleanup_service import cleanup_service
from app.repositories.image_repository import (
    image_repository,
    image_storage_location_repository,
    image_version_repository,
)


class ImageLifecycleService:
    async def archive_image(self, db: AsyncSession, image_id: uuid.UUID, user_id: uuid.UUID) -> Any:
        """Move image and all its preprocessed versions to cold storage and set status to 'archived'."""
        image = await image_service.get_image(db, image_id)
        if image.status == "archived":
            return image

        # 1. Archive primary storage location
        primary_loc = await image_storage_location_repository.get_primary_location(db, image_id)
        if primary_loc:
            archived_path = await archive_manager.archive_file(primary_loc.file_key_or_path)
            primary_loc.file_key_or_path = archived_path
            db.add(primary_loc)

        # 2. Archive all other version files
        versions = await image_version_repository.list_versions(db, image_id)
        for ver in versions:
            # Locate storage location for version
            locs = await image_storage_location_repository.list_locations(db, image_id)
            ver_loc = next((l for l in locs if l.image_version_id == ver.id), None)
            if ver_loc:
                archived_ver_path = await archive_manager.archive_file(ver_loc.file_key_or_path)
                ver_loc.file_key_or_path = archived_ver_path
                db.add(ver_loc)
                # Update path inside version object too
                ver.file_path = archived_ver_path
                db.add(ver)

        # 3. Update status
        image.status = "archived"
        db.add(image)

        # 4. Log Audit Trail
        await image_service.log_audit(db, image_id, user_id, "archive", {"filename": image.filename})
        await db.flush()
        return image

    async def restore_image(self, db: AsyncSession, image_id: uuid.UUID, user_id: uuid.UUID) -> Any:
        """Restore archived image assets back to active storage tier and set status to 'active'."""
        image = await image_service.get_image(db, image_id)
        if image.status != "archived":
            return image

        # 1. Restore primary file
        primary_loc = await image_storage_location_repository.get_primary_location(db, image_id)
        if primary_loc:
            restored_path = await archive_manager.restore_file(primary_loc.file_key_or_path)
            primary_loc.file_key_or_path = restored_path
            db.add(primary_loc)

        # 2. Restore version files
        versions = await image_version_repository.list_versions(db, image_id)
        for ver in versions:
            locs = await image_storage_location_repository.list_locations(db, image_id)
            ver_loc = next((l for l in locs if l.image_version_id == ver.id), None)
            if ver_loc:
                restored_ver_path = await archive_manager.restore_file(ver_loc.file_key_or_path)
                ver_loc.file_key_or_path = restored_ver_path
                db.add(ver_loc)
                ver.file_path = restored_ver_path
                db.add(ver)

        # 3. Update status
        image.status = "active"
        db.add(image)

        # 4. Log Audit
        await image_service.log_audit(db, image_id, user_id, "restore", {"filename": image.filename})
        await db.flush()
        return image

    async def soft_delete_image(self, db: AsyncSession, image_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Set status to 'deleted' and mark deleted_at timestamp in database."""
        return await image_service.delete_image(db, image_id, user_id)

    async def permanent_delete_image(self, db: AsyncSession, image_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Physically delete all associated files and purge all records from the database."""
        # 1. Fetch image to verify it exists and log info
        image = await image_repository.get_by_id(db, image_id, include_deleted=True)
        if not image:
            raise EntityNotFoundException(f"Image with ID {image_id} not found.")

        # 2. Delete physical storage assets
        await cleanup_service.delete_image_files(db, image_id)

        # 3. Permanent delete from database (cascade handles metadata, versions, storage, processing logs)
        await image_repository.delete(db, image_id)

        # 4. Log audit log (Since image is cascade-deleted, we log user activity generally in audit table)
        from app.services.activity_service import activity_service

        await activity_service.track_activity(
            db=db,
            action="image.permanent_delete",
            user_id=user_id,
            resource_type="image",
            resource_id=str(image_id),
            details={"filename": image.filename},
        )
        return True


image_lifecycle_service = ImageLifecycleService()
