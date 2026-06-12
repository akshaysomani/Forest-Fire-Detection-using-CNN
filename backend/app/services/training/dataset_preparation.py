import uuid
from typing import List, Dict, Any, Tuple
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import DatasetFile, DatasetVersion
from app.services.training.dataset_splitter import dataset_splitter
from app.services.training.dataset_validator import dataset_validator
from app.services.training.data_statistics import data_statistics


class DatasetPreparation:
    async def prepare_dataset(
        self,
        db: AsyncSession,
        dataset_id: uuid.UUID,
        version_str: str | None = None,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        seed: int = 42,
        min_files: int = 10
    ) -> Dict[str, Any]:
        """
        Orchestrate dataset preparation:
        1. Fetch files for the dataset (either matching a version snapshot or active unversioned files).
        2. Validate dataset size, labeling, diversity, and physical file existence.
        3. Split files into stratified train, validation, and test subsets.
        4. Compute dataset distribution and image statistics.
        Returns a dictionary containing split files and stats.
        """
        # Fetch files
        if version_str:
            # Find version snapshot
            version_query = select(DatasetVersion).where(
                and_(
                    DatasetVersion.dataset_id == dataset_id,
                    DatasetVersion.version_str == version_str,
                    DatasetVersion.deleted_at.is_(None)
                )
            )
            version_res = await db.execute(version_query)
            version = version_res.scalar_one_or_none()
            if not version:
                raise ValueError(f"Dataset version '{version_str}' was not found.")

            files_query = select(DatasetFile).where(
                and_(
                    DatasetFile.dataset_id == dataset_id,
                    DatasetFile.version_id == version.id,
                    DatasetFile.deleted_at.is_(None)
                )
            ).options(selectinload(DatasetFile.label))
        else:
            # Get active files (where version_id is None)
            files_query = select(DatasetFile).where(
                and_(
                    DatasetFile.dataset_id == dataset_id,
                    DatasetFile.version_id.is_(None),
                    DatasetFile.deleted_at.is_(None)
                )
            ).options(selectinload(DatasetFile.label))

        res = await db.execute(files_query)
        files = list(res.scalars().all())

        # Validate
        is_ready, error_msg = await dataset_validator.validate_dataset_files(files, min_files=min_files)
        if not is_ready:
            raise ValueError(f"Dataset preparation validation failed: {error_msg}")

        # Compute stats
        stats = await data_statistics.compute_statistics(files)

        # Split
        train_files, val_files, test_files = dataset_splitter.split_dataset(
            files=files,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            seed=seed
        )

        return {
            "train_files": train_files,
            "val_files": val_files,
            "test_files": test_files,
            "statistics": stats
        }


dataset_preparation = DatasetPreparation()
