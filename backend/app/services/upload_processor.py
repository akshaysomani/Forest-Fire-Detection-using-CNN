import io
import os
import zipfile
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal
from app.services.file_manager import file_manager
from app.services.file_validator import file_validator
from app.services.integrity_checker import integrity_checker
from app.services.image_service import image_service
from app.services.image_preprocessor import image_preprocessor
from app.services.thumbnail_service import thumbnail_service
from app.services.storage_service import storage_service
from app.repositories.image_repository import image_repository
from app.models.image import ImageProcessingLog


class UploadProcessor:
    async def process_zip_images(self, task_id: uuid.UUID, zip_bytes: bytes, owner_id: uuid.UUID, upload_source: str) -> None:
        """
        Extract and process images inside a ZIP archive in a background worker task:
        - Read ZIP stream
        - Filter image files
        - Validate, hash, save, metadata extraction, resize, thumbnail, storage locations
        - Log each status in DB
        """
        async with SessionLocal() as db:
            temp_dir = file_manager.create_temp_dir()
            success_count = 0
            failed_count = 0
            errors = {}

            try:
                zip_stream = io.BytesIO(zip_bytes)
                with zipfile.ZipFile(zip_stream) as zipf:
                    # Filter out directories and metadata files
                    namelist = [
                        name
                        for name in zipf.namelist()
                        if not name.endswith("/") and not os.path.basename(name).startswith(".")
                    ]

                    for name in namelist:
                        filename = os.path.basename(name)
                        sanitized_name = file_manager.sanitize_filename(filename)

                        # Check supported file extensions before parsing
                        ext = file_manager.get_file_extension(sanitized_name)
                        if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
                            failed_count += 1
                            errors[name] = f"Unsupported file extension: '{ext}'"
                            continue

                        # Extract bytes
                        with zipf.open(name) as file_entry:
                            entry_bytes = file_entry.read()
                            entry_stream = io.BytesIO(entry_bytes)

                        # Write image processing log for this image
                        # We don't have the image id yet, so we write it after image registration or create a placeholder image
                        start_time = datetime.now(timezone.utc)

                        # 1. Validate image
                        is_valid, error_msg, width, height = file_validator.validate_image(
                            file_stream=entry_stream, filename=sanitized_name
                        )
                        if not is_valid:
                            failed_count += 1
                            errors[name] = error_msg or "File validation failed."
                            continue

                        # 2. Check duplicate MD5 hash globally
                        md5_hash = file_manager.calculate_md5(entry_bytes)
                        is_duplicate, dup_id = await integrity_checker.check_global_duplication(db, md5_hash)
                        if is_duplicate:
                            failed_count += 1
                            errors[name] = f"Duplicate file check failed: An identical file already exists (ID: {dup_id})."
                            continue

                        try:
                            # 3. Create primary Image entity
                            image = await image_service.create_image(
                                db=db,
                                filename=sanitized_name,
                                original_filename=filename,
                                size_bytes=len(entry_bytes),
                                md5_hash=md5_hash,
                                owner_id=owner_id,
                                upload_source=upload_source,
                                mime_type=None,  # will be derived later or left empty
                            )

                            # Log processing start
                            proc_log = ImageProcessingLog(
                                image_id=image.id, operation="zip_extract_process", status="pending", started_at=start_time
                            )
                            db.add(proc_log)
                            await db.flush()

                            # 4. Extract EXIF & metadata
                            metadata_dict = image_preprocessor.extract_exif(entry_bytes)
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

                            # 5. Save original image to storage
                            storage_dest = f"images/{str(image.id)}/{sanitized_name}"
                            await storage_service.save_file(entry_bytes, storage_dest)

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
                                        else (
                                            settings.AZURE_CONTAINER
                                            if settings.STORAGE_PROVIDER == "azure"
                                            else settings.STORAGE_BASE_DIR
                                        )
                                    )
                                ),
                                file_key_or_path=storage_dest,
                                is_primary=True,
                            )

                            # 7. Generate preprocessed versions (Original, Resized CNN 224x224, WebP Thumbnail 128x128)
                            await image_service.add_version(
                                db=db,
                                image_id=image.id,
                                version_number=1,
                                purpose="original",
                                file_path=storage_dest,
                                size_bytes=len(entry_bytes),
                                md5_hash=md5_hash,
                            )

                            # Resized CNN Version (e.g. 224x224 PNG)
                            try:
                                resized_bytes = await image_preprocessor.resize_image(entry_bytes, 224, 224, format="PNG")
                                resized_hash = file_manager.calculate_md5(resized_bytes)
                                resized_dest = f"images/{str(image.id)}/versions/resized_{sanitized_name}"
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
                                            else (
                                                settings.AZURE_CONTAINER
                                                if settings.STORAGE_PROVIDER == "azure"
                                                else settings.STORAGE_BASE_DIR
                                            )
                                        )
                                    ),
                                    file_key_or_path=resized_dest,
                                    is_primary=False,
                                )
                            except Exception:
                                pass

                            # Thumbnail Version (e.g. 128x128 WEBP)
                            try:
                                thumb_bytes = await thumbnail_service.generate_thumbnail(
                                    entry_bytes, (128, 128), format="WEBP"
                                )
                                thumb_hash = file_manager.calculate_md5(thumb_bytes)
                                thumb_filename = sanitized_name.rsplit(".", 1)[0] + ".webp"
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
                                            else (
                                                settings.AZURE_CONTAINER
                                                if settings.STORAGE_PROVIDER == "azure"
                                                else settings.STORAGE_BASE_DIR
                                            )
                                        )
                                    ),
                                    file_key_or_path=thumb_dest,
                                    is_primary=False,
                                )
                            except Exception:
                                pass

                            # Update processing log status
                            proc_log.status = "success"
                            proc_log.completed_at = datetime.now(timezone.utc)
                            proc_log.duration_ms = (proc_log.completed_at - proc_log.started_at).total_seconds() * 1000
                            db.add(proc_log)

                            success_count += 1
                        except Exception as inner_e:
                            failed_count += 1
                            errors[name] = f"Internal storage mapping failed: {str(inner_e)}"

                    await db.commit()

            except Exception as outer_e:
                errors["zip_archive"] = f"Extraction failure: {str(outer_e)}"

            finally:
                file_manager.remove_dir(temp_dir)

            # Audit tracking using existing activity service/logs
            from app.services.activity_service import activity_service

            await activity_service.track_activity(
                db=db,
                action="image.zip_upload_background",
                user_id=owner_id,
                resource_type="zip_task",
                resource_id=str(task_id),
                details={"success_count": success_count, "failed_count": failed_count, "errors": errors},
            )
            await db.commit()


upload_processor = UploadProcessor()
