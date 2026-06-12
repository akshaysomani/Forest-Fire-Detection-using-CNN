import uuid
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundException
from app.models.dataset import DatasetFile, DatasetAuditLog
from app.repositories.label_repository import label_repository
from app.repositories.dataset_repository import dataset_repository


class LabelManager:
    async def assign_label_to_files(
        self,
        db: AsyncSession,
        dataset_id: uuid.UUID,
        file_ids: list[uuid.UUID],
        label_id: uuid.UUID | None,
        user_id: uuid.UUID,
    ) -> int:
        """
        Bulk assign a label (or remove it if label_id is None) to a list of file IDs inside a specific dataset.
        Returns the number of files updated.
        """
        # Verify dataset exists
        dataset = await dataset_repository.get_by_id(db, dataset_id)
        if not dataset:
            raise EntityNotFoundException(f"Dataset with ID {dataset_id} not found.")

        # Verify label exists if provided
        label_name = "None (Unlabeled)"
        if label_id:
            label = await label_repository.get_by_id(db, label_id)
            if not label:
                raise EntityNotFoundException(f"Label with ID {label_id} not found.")
            label_name = label.name

        # Execute bulk update
        query = (
            update(DatasetFile)
            .where(
                and_(
                    DatasetFile.dataset_id == dataset_id,
                    DatasetFile.id.in_(file_ids),
                    DatasetFile.deleted_at.is_(None)
                )
            )
            .values(label_id=label_id, updated_at=uuid.uuid4())  # Note: just trigger update, or let SQLAlchemy handle it
        )
        
        # Let's do update manually to count properly and set updated_at properly
        # Wait, using standard update values:
        query = (
            update(DatasetFile)
            .where(
                and_(
                    DatasetFile.dataset_id == dataset_id,
                    DatasetFile.id.in_(file_ids),
                    DatasetFile.deleted_at.is_(None)
                )
            )
            .values(label_id=label_id, updated_at=func.now() if hasattr(db, "bind") else None) # Wait, standard Python datetime works best to be provider-independent
        )
        # Let's import datetime
        from datetime import datetime
        query = (
            update(DatasetFile)
            .where(
                and_(
                    DatasetFile.dataset_id == dataset_id,
                    DatasetFile.id.in_(file_ids),
                    DatasetFile.deleted_at.is_(None)
                )
            )
            .values(label_id=label_id, updated_at=datetime.utcnow())
        )

        res = await db.execute(query)
        updated_count = res.rowcount

        # Log audit
        audit_log = DatasetAuditLog(
            dataset_id=dataset_id,
            user_id=user_id,
            action="dataset.label_files",
            details={
                "label_id": str(label_id) if label_id else None,
                "label_name": label_name,
                "file_count": len(file_ids),
                "updated_count": updated_count
            }
        )
        db.add(audit_log)
        await db.flush()

        return updated_count


# Import func for database-level timezone-agnostic operations
from sqlalchemy import func
label_manager = LabelManager()
