import hashlib
import logging
from typing import Tuple
from app.services.storage_service import storage_service
from app.core.exceptions import EntityNotFoundException

logger = logging.getLogger("model_registry.artifact_storage_service")


class ArtifactStorageService:
    @staticmethod
    async def verify_exists(storage_path: str) -> bool:
        """Checks if a file exists in the active storage provider."""
        return await storage_service.exists(storage_path)

    @staticmethod
    async def get_file_metadata(storage_path: str) -> Tuple[int, str]:
        """
        Reads file bytes from storage and computes:
        - file_size (in bytes)
        - sha256 checksum
        """
        if not await storage_service.exists(storage_path):
            raise EntityNotFoundException(f"Artifact at path '{storage_path}' not found in storage.")

        file_bytes = await storage_service.read_file(storage_path)
        file_size = len(file_bytes)

        sha256_hash = hashlib.sha256()
        sha256_hash.update(file_bytes)
        checksum = sha256_hash.hexdigest()

        return file_size, checksum

    @staticmethod
    async def read_artifact(storage_path: str) -> bytes:
        """Retrieves raw file bytes of the artifact."""
        return await storage_service.read_file(storage_path)


artifact_storage_service = ArtifactStorageService()
