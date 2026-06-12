import uuid
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundException, ValidationException
from app.models.dataset import DatasetLabel
from app.repositories.label_repository import label_repository


class LabelService:
    async def create_label(
        self, db: AsyncSession, name: str, description: str | None = None
    ) -> DatasetLabel:
        # Check if label name already exists
        existing = await label_repository.get_by_name(db, name)
        if existing:
            raise ValidationException(f"Label '{name}' already exists.")

        label = DatasetLabel(name=name, description=description)
        db.add(label)
        await db.flush()
        return label

    async def get_label_by_id(self, db: AsyncSession, id: uuid.UUID) -> DatasetLabel:
        label = await label_repository.get_by_id(db, id)
        if not label:
            raise EntityNotFoundException(f"Label with ID {id} not found.")
        return label

    async def get_label_by_name(self, db: AsyncSession, name: str) -> DatasetLabel:
        label = await label_repository.get_by_name(db, name)
        if not label:
            raise EntityNotFoundException(f"Label '{name}' not found.")
        return label

    async def list_labels(self, db: AsyncSession) -> Sequence[DatasetLabel]:
        return await label_repository.get_multi(db, limit=100)


label_service = LabelService()
