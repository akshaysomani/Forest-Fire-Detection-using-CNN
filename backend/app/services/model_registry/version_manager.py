import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.model_registry.model_repository import model_repository
from app.services.model_registry.model_version_service import model_version_service
from app.core.exceptions import ValidationException, EntityNotFoundException
from app.models.model_registry import ModelVersion


class VersionManager:
    @staticmethod
    async def validate_new_version(
        db: AsyncSession,
        model_id: uuid.UUID,
        version_str: str
    ) -> None:
        """
        Validates that a new version string is valid SemVer, and does not conflict
        with any existing versions for the specified model family.
        """
        if not model_version_service.is_valid_semver(version_str):
            raise ValidationException(
                f"Version string '{version_str}' is not a valid Semantic Version. "
                "Format must follow MAJOR.MINOR.PATCH (e.g., 1.0.0)."
            )

        # Check for duplication
        existing = await model_repository.get_version_by_number(db, model_id, version_str)
        if existing:
            raise ValidationException(
                f"Model version '{version_str}' is already registered for this model family."
            )

        # Optional: ensure version is greater than the latest version
        latest = await model_repository.get_latest_version(db, model_id)
        if latest:
            try:
                curr_maj, curr_min, curr_pat = model_version_service.parse_semver(latest.version)
                new_maj, new_min, new_pat = model_version_service.parse_semver(version_str)
                if (new_maj, new_min, new_pat) <= (curr_maj, curr_min, curr_pat):
                    raise ValidationException(
                        f"New version '{version_str}' must be greater than latest registered version '{latest.version}'."
                    )
            except ValueError:
                pass  # Ignore parse errors of legacy versions in SQLite if any exist

    @staticmethod
    async def resolve_next_version(
        db: AsyncSession,
        model_id: uuid.UUID,
        increment_type: str = "patch"
    ) -> str:
        """
        Calculates the next version string based on the latest registered version in the family.
        If no versions exist, defaults to '1.0.0'.
        """
        latest = await model_repository.get_latest_version(db, model_id)
        if not latest:
            return "1.0.0"
        
        try:
            return model_version_service.increment_version(latest.version, increment_type)
        except ValueError as e:
            raise ValidationException(str(e))

    @staticmethod
    def enforce_immutability(version: ModelVersion) -> None:
        """
        Ensures a model version is in 'Draft' state when edits to its details,
        hyperparameters, or checkpoints are attempted.
        """
        if version.status.lower().strip() != "draft":
            raise ValidationException(
                f"Model version '{version.version}' is in '{version.status}' state and is immutable. "
                "Edits are permitted only in 'Draft' status."
            )


version_manager = VersionManager()
