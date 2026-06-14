import uuid
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundException, ValidationException
from app.models.dataset import Dataset, DatasetCategory, DatasetLabel, DatasetAuditLog
from app.repositories.dataset_repository import dataset_repository, dataset_category_repository
from app.repositories.label_repository import label_repository
from app.schemas.dataset_schema import DatasetCreate, DatasetUpdate


class DatasetService:
    async def seed_categories_and_labels(self, db: AsyncSession) -> None:
        """Seed default dataset categories and labels into the database if they do not exist."""
        # 1. Categories Definition
        categories_def = {
            "Fire Images": "Curated images displaying active forest fires, flames, and hotspots.",
            "Non-Fire Images": "Curated forest and outdoor images without active fires or smoke.",
            "Validation Datasets": "Datasets reserved for hyperparameter tuning and validation.",
            "Test Datasets": "Datasets reserved strictly for testing and benchmarking models.",
            "Training Datasets": "Large-scale datasets designed for CNN model training.",
            "Research Datasets": "Experimental datasets for academic and exploratory studies.",
        }

        for name, desc in categories_def.items():
            cat = await dataset_category_repository.get_by_name(db, name)
            if not cat:
                new_cat = DatasetCategory(name=name, description=desc)
                db.add(new_cat)

        # 2. Labels Definition
        labels_def = {
            "Fire": "Active burning, open flames, or extreme thermal emissions.",
            "Non-Fire": "Normal environment, green foliage, water bodies, sky.",
            "Smoke": "Smoke plumes or hazy atmospheric columns signaling fire.",
            "Controlled Burn": "Planned forest management fires or agricultural burns.",
            "Human Activity": "Human presence, vehicles, machinery, structures in forestry.",
            "Unknown": "Unresolved or ambiguous image features needing review.",
        }

        for name, desc in labels_def.items():
            label = await label_repository.get_by_name(db, name)
            if not label:
                new_label = DatasetLabel(name=name, description=desc)
                db.add(new_label)

        await db.flush()

    async def create_dataset(self, db: AsyncSession, obj_in: DatasetCreate, user_id: uuid.UUID) -> Dataset:
        # Check if dataset name already exists
        existing = await dataset_repository.get_by_name(db, obj_in.name)
        if existing:
            raise ValidationException(f"Dataset with name '{obj_in.name}' already exists.")

        # Verify category exists
        category = await dataset_category_repository.get_by_id(db, obj_in.category_id)
        if not category:
            raise EntityNotFoundException(f"Category with ID {obj_in.category_id} not found.")

        # Create dataset
        db_obj = Dataset(
            name=obj_in.name,
            description=obj_in.description,
            category_id=obj_in.category_id,
            tags=obj_in.tags,
            user_id=user_id,
            status="active",
        )
        db.add(db_obj)
        await db.flush()

        # Log creation
        audit_log = DatasetAuditLog(
            dataset_id=db_obj.id,
            user_id=user_id,
            action="dataset.create",
            details={"name": db_obj.name, "category": category.name},
        )
        db.add(audit_log)
        await db.flush()

        # Refetch the dataset with eager loaded relationships to populate columns and avoid lazy loading
        from sqlalchemy.orm import selectinload

        query = select(Dataset).where(Dataset.id == db_obj.id).options(selectinload(Dataset.category))
        res = await db.execute(query)
        return res.scalar_one()

    async def get_dataset(self, db: AsyncSession, id: uuid.UUID) -> Dataset:
        db_obj = await dataset_repository.get_with_relations(db, id)
        if not db_obj:
            raise EntityNotFoundException(f"Dataset with ID {id} not found.")
        return db_obj

    async def update_dataset(self, db: AsyncSession, id: uuid.UUID, obj_in: DatasetUpdate, user_id: uuid.UUID) -> Dataset:
        db_obj = await self.get_dataset(db, id)

        update_data = obj_in.model_dump(exclude_unset=True)

        if "name" in update_data and update_data["name"] != db_obj.name:
            existing = await dataset_repository.get_by_name(db, update_data["name"])
            if existing:
                raise ValidationException(f"Dataset with name '{update_data['name']}' already exists.")

        if "category_id" in update_data:
            category = await dataset_category_repository.get_by_id(db, update_data["category_id"])
            if not category:
                raise EntityNotFoundException(f"Category with ID {update_data['category_id']} not found.")

        # Update properties
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)

        # Log audit
        audit_log = DatasetAuditLog(dataset_id=db_obj.id, user_id=user_id, action="dataset.update", details=update_data)
        db.add(audit_log)
        await db.flush()

        # Refetch the dataset with eager loaded relationships to populate columns and avoid lazy loading
        from sqlalchemy.orm import selectinload

        query = select(Dataset).where(Dataset.id == db_obj.id).options(selectinload(Dataset.category))
        res = await db.execute(query)
        return res.scalar_one()

    async def delete_dataset(self, db: AsyncSession, id: uuid.UUID, user_id: uuid.UUID) -> bool:
        db_obj = await self.get_dataset(db, id)

        # Soft delete the dataset
        await dataset_repository.soft_delete(db, id)

        # Log audit
        audit_log = DatasetAuditLog(dataset_id=id, user_id=user_id, action="dataset.delete", details={"name": db_obj.name})
        db.add(audit_log)
        await db.flush()
        return True

    async def get_categories(self, db: AsyncSession) -> Sequence[DatasetCategory]:
        return await dataset_category_repository.get_multi(db, limit=100)


dataset_service = DatasetService()
