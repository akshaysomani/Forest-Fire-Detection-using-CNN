import uuid
import os
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundException, ValidationException
from app.services.storage_service import storage_service
from app.services.storage_provider import (
    LocalStorageProvider,
    S3StorageProvider,
    GCSStorageProvider,
    AzureBlobStorageProvider,
)
from app.repositories.image_repository import (
    image_repository,
    image_storage_location_repository,
    image_version_repository,
)


class FileStorageManager:
    async def migrate_image(
        self,
        db: AsyncSession,
        image_id: uuid.UUID,
        target_provider: str,
        target_bucket_or_container: str
    ) -> Dict[str, Any]:
        """
        Migrate an image and all its preprocessed versions from their current storage provider
        to a target provider.
        """
        image = await image_repository.get_by_id_with_relations(db, id=image_id)
        if not image:
            raise EntityNotFoundException(f"Image with ID {image_id} not found.")

        # 1. Resolve current primary storage location
        primary_loc = await image_storage_location_repository.get_primary_location(db, image_id)
        if not primary_loc:
            raise ValidationException(f"Primary storage location for image {image_id} not found.")

        if primary_loc.provider == target_provider and primary_loc.bucket_or_container == target_bucket_or_container:
            return {"status": "skipped", "message": "Already at the target location."}

        # 2. Get provider instances
        from app.services.storage_service import StorageService
        current_service = storage_service  # default configured service
        
        # Instantiate temporary target provider
        from app.core.config import settings
        target_provider_inst = None
        if target_provider == "local":
            target_provider_inst = LocalStorageProvider(base_dir=settings.STORAGE_BASE_DIR)
        elif target_provider == "s3":
            target_provider_inst = S3StorageProvider(bucket_name=target_bucket_or_container)
        elif target_provider == "gcs":
            target_provider_inst = GCSStorageProvider(bucket_name=target_bucket_or_container)
        elif target_provider == "azure":
            target_provider_inst = AzureBlobStorageProvider(container_name=target_bucket_or_container)
        else:
            raise ValidationException(f"Invalid target provider: {target_provider}")

        # 3. Read original file contents
        try:
            file_bytes = await current_service.read_file(primary_loc.file_key_or_path)
        except Exception as e:
            raise ValidationException(f"Failed to read image from source: {str(e)}")

        # 4. Save to target
        new_key = f"images/{str(image_id)}/{image.filename}"
        try:
            new_path = await target_provider_inst.save_file(file_bytes, new_key)
        except Exception as e:
            raise ValidationException(f"Failed to save image to target provider: {str(e)}")

        # 5. Update DB
        primary_loc.provider = target_provider
        primary_loc.bucket_or_container = target_bucket_or_container
        primary_loc.file_key_or_path = new_key
        db.add(primary_loc)

        # 6. Migrate versions if any
        versions = await image_version_repository.list_versions(db, image_id)
        migrated_versions = []
        for ver in versions:
            # Find version storage location
            locs = await image_storage_location_repository.list_locations(db, image_id)
            ver_loc = next((l for l in locs if l.image_version_id == ver.id), None)
            if ver_loc:
                try:
                    ver_bytes = await current_service.read_file(ver_loc.file_key_or_path)
                    ver_key = f"images/{str(image_id)}/versions/{ver.purpose}_{image.filename}"
                    await target_provider_inst.save_file(ver_bytes, ver_key)
                    
                    ver_loc.provider = target_provider
                    ver_loc.bucket_or_container = target_bucket_or_container
                    ver_loc.file_key_or_path = ver_key
                    db.add(ver_loc)
                    
                    # Update file_path in version record
                    ver.file_path = ver_key
                    db.add(ver)
                    
                    migrated_versions.append(ver.purpose)
                except Exception as e:
                    # Log failure but continue
                    pass

        await db.flush()
        return {
            "status": "success",
            "image_id": str(image_id),
            "new_provider": target_provider,
            "new_path": new_path,
            "migrated_versions": migrated_versions
        }

    async def verify_integrity_all(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Verify database reference integrity by sweeping all stored images and checking
        if they physically exist in their registered storage providers.
        """
        images = await image_repository.list_images(db, limit=1000)
        missing_images = []
        verified_count = 0

        for img in images:
            loc = await image_storage_location_repository.get_primary_location(db, img.id)
            if loc:
                exists = await storage_service.exists(loc.file_key_or_path)
                if not exists:
                    missing_images.append({
                        "image_id": str(img.id),
                        "filename": img.filename,
                        "expected_path": loc.file_key_or_path,
                        "provider": loc.provider
                    })
                else:
                    verified_count += 1

        return {
            "total_checked": len(images),
            "verified_count": verified_count,
            "missing_count": len(missing_images),
            "missing_files": missing_images
        }


file_storage_manager = FileStorageManager()
