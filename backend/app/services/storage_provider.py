import abc
import os
import shutil
from typing import BinaryIO


class StorageProvider(abc.ABC):
    @abc.abstractmethod
    async def save_file(self, file_data: bytes, destination_path: str) -> str:
        """Save bytes payload to the storage destination. Returns the relative or absolute storage path."""
        pass

    @abc.abstractmethod
    async def save_stream(self, file_stream: BinaryIO, destination_path: str) -> str:
        """Save a file-like object stream to the storage destination. Returns the path."""
        pass

    @abc.abstractmethod
    async def read_file(self, source_path: str) -> bytes:
        """Read file contents as bytes."""
        pass

    @abc.abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from storage."""
        pass

    @abc.abstractmethod
    async def exists(self, file_path: str) -> bool:
        """Check if file exists in storage."""
        pass


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: str = "./storage"):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_full_path(self, relative_path: str) -> str:
        # Prevent directory traversal by cleaning path and joining safely
        clean_path = os.path.normpath(relative_path).lstrip("\\/")
        return os.path.join(self.base_dir, clean_path)

    async def save_file(self, file_data: bytes, destination_path: str) -> str:
        full_path = self._get_full_path(destination_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(file_data)
        return destination_path

    async def save_stream(self, file_stream: BinaryIO, destination_path: str) -> str:
        full_path = self._get_full_path(destination_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            shutil.copyfileobj(file_stream, f)
        return destination_path

    async def read_file(self, source_path: str) -> bytes:
        full_path = self._get_full_path(source_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found at: {source_path}")
        with open(full_path, "rb") as f:
            return f.read()

    async def delete_file(self, file_path: str) -> bool:
        full_path = self._get_full_path(file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False

    async def exists(self, file_path: str) -> bool:
        full_path = self._get_full_path(file_path)
        return os.path.exists(full_path)


class S3StorageProvider(StorageProvider):
    """Placeholder for AWS S3 Storage Provider implementation."""
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name

    async def save_file(self, file_data: bytes, destination_path: str) -> str:
        # In a real S3 implementation, use boto3 to upload to S3 bucket
        # e.g., s3_client.put_object(Bucket=self.bucket_name, Key=destination_path, Body=file_data)
        return f"s3://{self.bucket_name}/{destination_path}"

    async def save_stream(self, file_stream: BinaryIO, destination_path: str) -> str:
        return f"s3://{self.bucket_name}/{destination_path}"

    async def read_file(self, source_path: str) -> bytes:
        raise NotImplementedError("S3 read_file is not implemented.")

    async def delete_file(self, file_path: str) -> bool:
        return True

    async def exists(self, file_path: str) -> bool:
        return False


class GCSStorageProvider(StorageProvider):
    """Placeholder for Google Cloud Storage Provider implementation."""
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name

    async def save_file(self, file_data: bytes, destination_path: str) -> str:
        return f"gs://{self.bucket_name}/{destination_path}"

    async def save_stream(self, file_stream: BinaryIO, destination_path: str) -> str:
        return f"gs://{self.bucket_name}/{destination_path}"

    async def read_file(self, source_path: str) -> bytes:
        raise NotImplementedError("GCS read_file is not implemented.")

    async def delete_file(self, file_path: str) -> bool:
        return True

    async def exists(self, file_path: str) -> bool:
        return False


class AzureBlobStorageProvider(StorageProvider):
    """Placeholder for Azure Blob Storage Provider implementation."""
    def __init__(self, container_name: str):
        self.container_name = container_name

    async def save_file(self, file_data: bytes, destination_path: str) -> str:
        return f"azure://{self.container_name}/{destination_path}"

    async def save_stream(self, file_stream: BinaryIO, destination_path: str) -> str:
        return f"azure://{self.container_name}/{destination_path}"

    async def read_file(self, source_path: str) -> bytes:
        raise NotImplementedError("Azure Blob read_file is not implemented.")

    async def delete_file(self, file_path: str) -> bool:
        return True

    async def exists(self, file_path: str) -> bool:
        return False
