import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundException
from app.models.dataset import DatasetUploadHistory
from app.repositories.dataset_repository import dataset_upload_history_repository


class UploadManager:
    """Manager for querying dataset file upload histories and status."""

    async def get_upload_status(self, db: AsyncSession, history_id: uuid.UUID) -> DatasetUploadHistory:
        """Fetch the detailed extraction progress of a ZIP dataset upload."""
        history = await dataset_upload_history_repository.get_by_id(db, history_id)
        if not history:
            raise EntityNotFoundException(f"Upload history item with ID {history_id} not found.")
        return history

    async def get_dataset_upload_history(
        self, db: AsyncSession, dataset_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[DatasetUploadHistory]:
        """Fetch a chronological list of uploads performed on a dataset."""
        return await dataset_upload_history_repository.get_by_dataset(db, dataset_id, skip, limit)


upload_manager = UploadManager()
