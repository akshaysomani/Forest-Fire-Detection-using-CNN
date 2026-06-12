import io
import uuid
from typing import BinaryIO, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.file_validator import file_validator
from app.services.file_manager import file_manager
from app.repositories.dataset_repository import dataset_file_repository


class DatasetValidator:
    @staticmethod
    async def validate_and_hash_file(
        db: AsyncSession,
        dataset_id: uuid.UUID,
        file_stream: BinaryIO,
        filename: str,
        mime_type: str | None = None,
        max_size_bytes: int = 10 * 1024 * 1024,
    ) -> Dict[str, Any]:
        """
        Orchestrate validation for a single file:
        1. Calculate MD5 hash
        2. Validate image format, corruption, size, and resolution
        3. Check database for existing MD5 collision in the dataset
        Returns a detailed validation report.
        """
        # Clean seek position
        try:
            file_stream.seek(0)
        except Exception:
            pass

        # Calculate md5 hash first
        md5_hash = file_manager.calculate_md5_stream(file_stream)

        # Validate file size
        try:
            file_stream.seek(0, 2)
            file_size = file_stream.tell()
            file_stream.seek(0)
        except Exception:
            file_size = 0

        # Run file validation
        is_valid, error_msg, width, height = file_validator.validate_image(
            file_stream=file_stream,
            filename=filename,
            mime_type=mime_type,
            max_size_bytes=max_size_bytes,
        )

        is_duplicate = False
        if is_valid:
            # Check DB for duplicate MD5 hash in active files of this dataset
            dup_file = await dataset_file_repository.get_by_md5(db, dataset_id, md5_hash)
            if dup_file:
                is_duplicate = True
                is_valid = False
                error_msg = f"Duplicate file check failed: An identical file already exists in the dataset (ID: {dup_file.id})."

        return {
            "filename": filename,
            "is_valid": is_valid,
            "error": error_msg,
            "width": width,
            "height": height,
            "md5_hash": md5_hash,
            "file_size": file_size,
            "is_duplicate": is_duplicate
        }


dataset_validator = DatasetValidator()
