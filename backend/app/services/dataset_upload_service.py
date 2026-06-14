import uuid
from typing import List, Dict, Any
from fastapi import UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundException, ValidationException
from app.models.dataset import DatasetFile, DatasetUploadHistory, DatasetAuditLog
from app.repositories.dataset_repository import (
    dataset_repository,
    dataset_file_repository,
    dataset_upload_history_repository,
)
from app.repositories.label_repository import label_repository
from app.services.dataset_validator import dataset_validator
from app.services.storage_service import storage_service
from app.services.file_manager import file_manager
from app.services.dataset_processor import dataset_processor


class DatasetUploadService:
    async def upload_single_file(
        self,
        db: AsyncSession,
        dataset_id: uuid.UUID,
        upload_file: UploadFile,
        user_id: uuid.UUID,
        label_id: uuid.UUID | None = None,
    ) -> DatasetFile:
        # Verify dataset exists
        dataset = await dataset_repository.get_by_id(db, dataset_id)
        if not dataset:
            raise EntityNotFoundException(f"Dataset with ID {dataset_id} not found.")

        # Verify label exists if provided
        if label_id:
            label = await label_repository.get_by_id(db, label_id)
            if not label:
                raise EntityNotFoundException(f"Label with ID {label_id} not found.")

        # Read stream
        file_bytes = await upload_file.read()
        file_stream = io.BytesIO(file_bytes)
        filename = file_manager.sanitize_filename(upload_file.filename or "uploaded_image")

        # Validate file
        val_report = await dataset_validator.validate_and_hash_file(
            db=db, dataset_id=dataset_id, file_stream=file_stream, filename=filename, mime_type=upload_file.content_type
        )

        if not val_report["is_valid"]:
            raise ValidationException(val_report["error"] or "File validation failed.")

        # Save to storage
        storage_dest = f"datasets/{str(dataset_id)}/raw/{filename}"
        await storage_service.save_file(file_bytes, storage_dest)

        # Register in DB
        db_file = DatasetFile(
            dataset_id=dataset_id,
            version_id=None,
            file_path=storage_dest,
            filename=filename,
            file_size=val_report["file_size"],
            mime_type=upload_file.content_type,
            md5_hash=val_report["md5_hash"],
            label_id=label_id,
            metadata_json={"width": val_report["width"], "height": val_report["height"]},
        )
        db.add(db_file)

        # Audit Log
        audit = DatasetAuditLog(
            dataset_id=dataset_id,
            user_id=user_id,
            action="dataset.upload_file",
            details={"filename": filename, "md5_hash": val_report["md5_hash"], "file_size": val_report["file_size"]},
        )
        db.add(audit)
        await db.flush()

        return db_file

    async def upload_bulk_files(
        self, db: AsyncSession, dataset_id: uuid.UUID, upload_files: List[UploadFile], user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Process multiple image uploads. Returns statistics of succeeded and failed files.
        """
        dataset = await dataset_repository.get_by_id(db, dataset_id)
        if not dataset:
            raise EntityNotFoundException(f"Dataset with ID {dataset_id} not found.")

        success_files = []
        failed_files = []

        for upload_file in upload_files:
            file_bytes = await upload_file.read()
            file_stream = io.BytesIO(file_bytes)
            filename = file_manager.sanitize_filename(upload_file.filename or "bulk_image")

            val_report = await dataset_validator.validate_and_hash_file(
                db=db, dataset_id=dataset_id, file_stream=file_stream, filename=filename, mime_type=upload_file.content_type
            )

            if val_report["is_valid"]:
                storage_dest = f"datasets/{str(dataset_id)}/raw/{filename}"
                await storage_service.save_file(file_bytes, storage_dest)

                db_file = DatasetFile(
                    dataset_id=dataset_id,
                    version_id=None,
                    file_path=storage_dest,
                    filename=filename,
                    file_size=val_report["file_size"],
                    mime_type=upload_file.content_type,
                    md5_hash=val_report["md5_hash"],
                    label_id=None,
                    metadata_json={"width": val_report["width"], "height": val_report["height"]},
                )
                db.add(db_file)
                success_files.append(filename)
            else:
                failed_files.append({"filename": filename, "error": val_report["error"]})

        # Log audit if anything succeeded
        if success_files:
            audit = DatasetAuditLog(
                dataset_id=dataset_id,
                user_id=user_id,
                action="dataset.upload_bulk",
                details={"success_count": len(success_files), "failed_count": len(failed_files)},
            )
            db.add(audit)
            await db.flush()

        return {
            "dataset_id": dataset_id,
            "total_files": len(upload_files),
            "success_count": len(success_files),
            "failed_count": len(failed_files),
            "success_files": success_files,
            "failed_files": failed_files,
        }

    async def upload_zip_dataset(
        self,
        db: AsyncSession,
        dataset_id: uuid.UUID,
        zip_file: UploadFile,
        user_id: uuid.UUID,
        background_tasks: BackgroundTasks,
    ) -> DatasetUploadHistory:
        """
        Receives ZIP upload, registers a pending upload history item, and schedules a background extractor job.
        """
        dataset = await dataset_repository.get_by_id(db, dataset_id)
        if not dataset:
            raise EntityNotFoundException(f"Dataset with ID {dataset_id} not found.")

        # Read zip bytes
        zip_bytes = await zip_file.read()

        # Simple size validation
        if len(zip_bytes) == 0:
            raise ValidationException("ZIP archive is empty.")

        # Verify magic number for ZIP files
        if not zip_file.filename.lower().endswith(".zip") and zip_bytes[:4] != b"PK\x03\x04":
            raise ValidationException("File is not a valid ZIP archive.")

        # Save history item
        history = DatasetUploadHistory(
            dataset_id=dataset_id,
            user_id=user_id,
            status="pending",
            upload_type="zip",
            original_filename=zip_file.filename,
            total_files=0,
            processed_files=0,
            failed_files=0,
        )
        db.add(history)
        await db.flush()

        # Dispatch extraction task to FastAPI background tasks
        background_tasks.add_task(
            dataset_processor.process_zip_upload,
            history_id=history.id,
            dataset_id=dataset_id,
            zip_file_bytes=zip_bytes,
            user_id=user_id,
        )

        return history


import io

dataset_upload_service = DatasetUploadService()
