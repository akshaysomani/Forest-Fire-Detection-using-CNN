import uuid
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundException, ValidationException
from app.models.dataset import DatasetVersion, DatasetAuditLog
from app.repositories.dataset_repository import (
    dataset_repository,
    dataset_version_repository,
    dataset_file_repository,
)
from app.services.dataset_snapshot_service import dataset_snapshot_service


class DatasetVersionService:
    async def create_version(
        self,
        db: AsyncSession,
        dataset_id: uuid.UUID,
        version_str: str,
        description: str | None,
        user_id: uuid.UUID,
        creator_username: str,
    ) -> DatasetVersion:
        # Verify dataset exists
        dataset = await dataset_repository.get_by_id(db, dataset_id)
        if not dataset:
            raise EntityNotFoundException(f"Dataset with ID {dataset_id} not found.")

        # Check if version already exists
        existing = await dataset_version_repository.get_by_dataset_and_version(db, dataset_id, version_str)
        if existing:
            raise ValidationException(f"Version '{version_str}' already exists for this dataset.")

        # Fetch active files (which will be frozen in this snapshot)
        active_files = await dataset_file_repository.get_active_files_by_dataset(db, dataset_id)
        if not active_files:
            raise ValidationException("Cannot create a version snapshot for an empty dataset. Please upload files first.")

        # Create zip snapshot and metadata
        snapshot_path, size_bytes, file_count, metadata_json = await dataset_snapshot_service.create_version_snapshot(
            dataset_id=dataset_id,
            version_str=version_str,
            files=active_files,
            creator_username=creator_username,
            description=description,
        )

        # Create DB Version
        db_version = DatasetVersion(
            dataset_id=dataset_id,
            version_str=version_str,
            description=description,
            status="active",
            user_id=user_id,
            metadata_json=metadata_json,
            snapshot_path=snapshot_path,
            size_bytes=size_bytes,
            file_count=file_count,
        )
        db.add(db_version)
        await db.flush()

        # Update files: lock them into this version
        for f in active_files:
            f.version_id = db_version.id
            db.add(f)

        # Log audit
        audit_log = DatasetAuditLog(
            dataset_id=dataset_id,
            user_id=user_id,
            action="dataset.version_create",
            details={
                "version_id": str(db_version.id),
                "version_str": version_str,
                "file_count": file_count,
                "size_bytes": size_bytes,
            },
        )
        db.add(audit_log)
        await db.flush()

        return db_version

    async def get_versions(self, db: AsyncSession, dataset_id: uuid.UUID) -> Sequence[DatasetVersion]:
        # Verify dataset exists
        dataset = await dataset_repository.get_by_id(db, dataset_id)
        if not dataset:
            raise EntityNotFoundException(f"Dataset with ID {dataset_id} not found.")
        return await dataset_version_repository.get_by_dataset(db, dataset_id)

    async def get_version_by_id(self, db: AsyncSession, version_id: uuid.UUID) -> DatasetVersion:
        version = await dataset_version_repository.get_by_id(db, version_id)
        if not version:
            raise EntityNotFoundException(f"Version with ID {version_id} not found.")
        return version


dataset_version_service = DatasetVersionService()
