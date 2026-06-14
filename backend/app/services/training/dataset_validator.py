import uuid
from typing import List, Tuple
from app.models.dataset import DatasetFile
from app.services.storage_service import storage_service


class DatasetValidator:
    @staticmethod
    async def validate_dataset_files(files: List[DatasetFile], min_files: int = 10) -> Tuple[bool, str | None]:
        """
        Validate training readiness of dataset files:
        1. Checks minimum count of files.
        2. Ensures all files have label_id assigned.
        3. Verifies that there are at least 2 distinct classes (labels) present.
        4. Validates that the physical file actually exists in storage.
        """
        if len(files) < min_files:
            return (
                False,
                f"Dataset has insufficient images. Found {len(files)}, but at least {min_files} are required for training.",
            )

        labels = set()
        missing_labels_count = 0

        for f in files:
            if not f.label_id:
                missing_labels_count += 1
            else:
                labels.add(f.label_id)

        if missing_labels_count > 0:
            return (
                False,
                f"Dataset contains {missing_labels_count} unlabeled images. All images must be labeled before training.",
            )

        if len(labels) < 2:
            return (
                False,
                f"Dataset lacks class diversity. Found {len(labels)} class(es), but classification requires at least 2 distinct labels (e.g., Fire and Non-Fire).",
            )

        # Verify storage existence for all files
        for f in files:
            file_exists = await storage_service.exists(f.file_path)
            if not file_exists:
                return False, f"Physical file missing in storage for image: '{f.filename}' (Path: {f.file_path})."

        return True, None


dataset_validator = DatasetValidator()
