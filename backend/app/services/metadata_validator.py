from typing import Any, Dict, List, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.dataset import DatasetLabel


class MetadataValidator:
    @staticmethod
    async def validate_label_consistency(
        db: AsyncSession,
        labels: List[str]
    ) -> Tuple[bool, str | None]:
        """
        Validate that the provided labels are supported by the system.
        Returns (is_consistent, error_message)
        """
        if not labels:
            return True, None

        # Fetch all valid labels from DB
        query = select(DatasetLabel.name).where(DatasetLabel.deleted_at.is_(None))
        result = await db.execute(query)
        valid_labels = {name.lower() for name in result.scalars().all()}

        for label in labels:
            if label.lower() not in valid_labels:
                return False, f"Unsupported label: '{label}'. Supported labels are: {list(valid_labels)}"

        return True, None

    @staticmethod
    def validate_metadata_structure(
        metadata: Dict[str, Any]
    ) -> Tuple[bool, str | None]:
        """
        Validate dataset metadata schema structure.
        """
        if not isinstance(metadata, dict):
            return False, "Metadata must be a JSON object (dictionary)."
        
        # Check standard properties if specified, e.g. class distributions, description splits, etc.
        if "class_distribution" in metadata:
            dist = metadata["class_distribution"]
            if not isinstance(dist, dict):
                return False, "'class_distribution' in metadata must be a JSON object mapping labels to counts."
            for label, count in dist.items():
                if not isinstance(count, int) or count < 0:
                    return False, f"Count for label '{label}' in 'class_distribution' must be a non-negative integer."

        return True, None


metadata_validator = MetadataValidator()
