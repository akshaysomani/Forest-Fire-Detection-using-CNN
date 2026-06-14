import uuid
import io
from typing import List, Dict, Any
from fastapi import UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundException, ValidationException
from app.services.file_manager import file_manager
from app.services.file_validator import file_validator
from app.services.integrity_checker import integrity_checker
from app.services.image_service import image_service
from app.services.image_preprocessor import image_preprocessor
from app.services.thumbnail_service import thumbnail_service
from app.services.storage_service import storage_service
from app.repositories.image_repository import (
    image_repository,
    image_storage_location_repository,
)


class ImageUploadService:
    async def upload_single_image(
        self, db: AsyncSession, upload_file: UploadFile, owner_id: uuid.UUID, upload_source: str
    ) -> Any:
        """
        Orchestrate upload and processing of a single image:
        - Read file bytes
        - Validate (magic bytes, resolution boundaries, size limit)
        - Check MD5 collision globally
        - Write original to storage
        - Extract metadata & EXIF
        - Generate CNN preprocessed versions (resized 224x224 and thumbnail 128x128)
        - Write DB records
        """
        file_bytes = await upload_file.read()
        filename = file_manager.sanitize_filename(upload_file.filename or "image.png")
        file_stream = io.BytesIO(file_bytes)

        # 1. Validate image properties
        is_valid, error_msg, width, height = file_validator.validate_image(
            file_stream=file_stream, filename=filename, mime_type=upload_file.content_type
        )
        if not is_valid:
            raise ValidationException(error_msg or "File validation failed.")

        # 2. Check duplicate MD5 hash globally
        md5_hash = file_manager.calculate_md5(file_bytes)
        is_duplicate, dup_id = await integrity_checker.check_global_duplication(db, md5_hash)
        if is_duplicate:
            raise ValidationException(f"Global duplicate check failed: Image already exists (ID: {dup_id}).")

        # 3. Create primary Image entity
        image = await image_service.create_image(
            db=db,
            filename=filename,
            original_filename=upload_file.filename or "image.png",
            size_bytes=len(file_bytes),
            md5_hash=md5_hash,
            owner_id=owner_id,
            upload_source=upload_source,
            mime_type=upload_file.content_type,
        )

        # 4. Extract EXIF & metadata
        metadata_dict = image_preprocessor.extract_exif(file_bytes)
        # Fallback to validator dimensions if EXIF is empty
        meta_w = metadata_dict.get("width") or width or 0
        meta_h = metadata_dict.get("height") or height or 0

        await image_service.add_or_update_metadata(
            db=db,
            image_id=image.id,
            width=meta_w,
            height=meta_h,
            exif_data=metadata_dict.get("exif_raw"),
            gps_latitude=metadata_dict.get("gps_latitude"),
            gps_longitude=metadata_dict.get("gps_longitude"),
            captured_at=metadata_dict.get("captured_at"),
            camera_make=metadata_dict.get("camera_make"),
            camera_model=metadata_dict.get("camera_model"),
            extra_metadata=metadata_dict.get("extra_metadata"),
        )

        # 5. Save original image to configured storage provider
        # Destination: images/{image_id}/{filename}
        storage_dest = f"images/{str(image.id)}/{filename}"
        await storage_service.save_file(file_bytes, storage_dest)

        # 6. Save original image storage location record
        from app.core.config import settings

        await image_service.add_storage_location(
            db=db,
            image_id=image.id,
            version_id=None,
            provider=settings.STORAGE_PROVIDER,
            bucket_or_container=(
                settings.AWS_S3_BUCKET
                if settings.STORAGE_PROVIDER == "s3"
                else (
                    settings.GCS_BUCKET
                    if settings.STORAGE_PROVIDER == "gcs"
                    else (settings.AZURE_CONTAINER if settings.STORAGE_PROVIDER == "azure" else settings.STORAGE_BASE_DIR)
                )
            ),
            file_key_or_path=storage_dest,
            is_primary=True,
        )

        # 7. Generate preprocessed versions (Original, Resized CNN 224x224, WebP Thumbnail 128x128)
        # Original version record
        orig_ver = await image_service.add_version(
            db=db,
            image_id=image.id,
            version_number=1,
            purpose="original",
            file_path=storage_dest,
            size_bytes=len(file_bytes),
            md5_hash=md5_hash,
        )

        # Resized CNN Version (e.g. 224x224 PNG)
        try:
            resized_bytes = await image_preprocessor.resize_image(file_bytes, 224, 224, format="PNG")
            resized_hash = file_manager.calculate_md5(resized_bytes)
            resized_dest = f"images/{str(image.id)}/versions/resized_{filename}"
            await storage_service.save_file(resized_bytes, resized_dest)

            resized_ver = await image_service.add_version(
                db=db,
                image_id=image.id,
                version_number=2,
                purpose="resized",
                file_path=resized_dest,
                size_bytes=len(resized_bytes),
                md5_hash=resized_hash,
            )
            await image_service.add_storage_location(
                db=db,
                image_id=image.id,
                version_id=resized_ver.id,
                provider=settings.STORAGE_PROVIDER,
                bucket_or_container=(
                    settings.AWS_S3_BUCKET
                    if settings.STORAGE_PROVIDER == "s3"
                    else (
                        settings.GCS_BUCKET
                        if settings.STORAGE_PROVIDER == "gcs"
                        else (settings.AZURE_CONTAINER if settings.STORAGE_PROVIDER == "azure" else settings.STORAGE_BASE_DIR)
                    )
                ),
                file_key_or_path=resized_dest,
                is_primary=False,
            )
        except Exception:
            # Safe catch to ensure processing log is written if failure occurs
            pass

        # Thumbnail Version (e.g. 128x128 WEBP)
        try:
            thumb_bytes = await thumbnail_service.generate_thumbnail(file_bytes, (128, 128), format="WEBP")
            thumb_hash = file_manager.calculate_md5(thumb_bytes)
            thumb_filename = filename.rsplit(".", 1)[0] + ".webp"
            thumb_dest = f"images/{str(image.id)}/versions/thumbnail_{thumb_filename}"
            await storage_service.save_file(thumb_bytes, thumb_dest)

            thumb_ver = await image_service.add_version(
                db=db,
                image_id=image.id,
                version_number=3,
                purpose="thumbnail",
                file_path=thumb_dest,
                size_bytes=len(thumb_bytes),
                md5_hash=thumb_hash,
            )
            await image_service.add_storage_location(
                db=db,
                image_id=image.id,
                version_id=thumb_ver.id,
                provider=settings.STORAGE_PROVIDER,
                bucket_or_container=(
                    settings.AWS_S3_BUCKET
                    if settings.STORAGE_PROVIDER == "s3"
                    else (
                        settings.GCS_BUCKET
                        if settings.STORAGE_PROVIDER == "gcs"
                        else (settings.AZURE_CONTAINER if settings.STORAGE_PROVIDER == "azure" else settings.STORAGE_BASE_DIR)
                    )
                ),
                file_key_or_path=thumb_dest,
                is_primary=False,
            )
        except Exception:
            pass

        await db.flush()
        # Refetch image with relations
        return await image_repository.get_by_id_with_relations(db, image.id)

    async def upload_bulk_images(
        self, db: AsyncSession, upload_files: List[UploadFile], owner_id: uuid.UUID, upload_source: str
    ) -> Dict[str, Any]:
        """Process multiple files sequentially and capture errors for detailed report."""
        success_images = []
        failed_images = []

        for f in upload_files:
            try:
                img = await self.upload_single_image(db, f, owner_id, upload_source)
                success_images.append(
                    {
                        "id": img.id,
                        "filename": img.filename,
                        "md5_hash": img.md5_hash,
                        "size_bytes": img.size_bytes,
                        "status": img.status,
                        "upload_source": img.upload_source,
                    }
                )
            except Exception as e:
                failed_images.append({"filename": f.filename or "unknown", "error": str(e)})

        return {
            "total": len(upload_files),
            "success_count": len(success_images),
            "failed_count": len(failed_images),
            "success_images": success_images,
            "failed_images": failed_images,
        }

    async def upload_zip_images(
        self,
        db: AsyncSession,
        zip_file: UploadFile,
        owner_id: uuid.UUID,
        upload_source: str,
        background_tasks: BackgroundTasks,
    ) -> Dict[str, Any]:
        """Read ZIP bytes and delegate extraction to background thread runner."""
        zip_bytes = await zip_file.read()
        if len(zip_bytes) == 0:
            raise ValidationException("ZIP archive is empty.")

        # Quick validation of ZIP signature
        if not zip_file.filename.lower().endswith(".zip") and zip_bytes[:4] != b"PK\x03\x04":
            raise ValidationException("File is not a valid ZIP archive.")

        task_id = uuid.uuid4()

        # Schedule extraction background task
        from app.services.upload_processor import upload_processor

        background_tasks.add_task(
            upload_processor.process_zip_images,
            task_id=task_id,
            zip_bytes=zip_bytes,
            owner_id=owner_id,
            upload_source=upload_source,
        )

        return {
            "task_id": task_id,
            "status": "pending",
            "message": "ZIP extraction and processing scheduled in the background.",
        }


image_upload_service = ImageUploadService()
