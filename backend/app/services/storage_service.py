from typing import BinaryIO
from app.core.config import settings
from app.services.storage_provider import (
    StorageProvider,
    LocalStorageProvider,
    S3StorageProvider,
    GCSStorageProvider,
    AzureBlobStorageProvider,
)


class StorageService:
    def __init__(self):
        provider_type = settings.STORAGE_PROVIDER.lower()
        if provider_type == "local":
            self.provider: StorageProvider = LocalStorageProvider(base_dir=settings.STORAGE_BASE_DIR)
        elif provider_type == "s3":
            self.provider = S3StorageProvider(bucket_name=settings.AWS_S3_BUCKET)
        elif provider_type == "gcs":
            self.provider = GCSStorageProvider(bucket_name=settings.GCS_BUCKET)
        elif provider_type == "azure":
            self.provider = AzureBlobStorageProvider(container_name=settings.AZURE_CONTAINER)
        else:
            # Fallback to local
            self.provider = LocalStorageProvider(base_dir=settings.STORAGE_BASE_DIR)

    async def save_file(self, file_data: bytes, destination_path: str) -> str:
        return await self.provider.save_file(file_data, destination_path)

    async def save_stream(self, file_stream: BinaryIO, destination_path: str) -> str:
        return await self.provider.save_stream(file_stream, destination_path)

    async def read_file(self, source_path: str) -> bytes:
        return await self.provider.read_file(source_path)

    async def delete_file(self, file_path: str) -> bool:
        return await self.provider.delete_file(file_path)

    async def exists(self, file_path: str) -> bool:
        return await self.provider.exists(file_path)


storage_service = StorageService()
