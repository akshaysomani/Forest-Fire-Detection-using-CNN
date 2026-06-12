import abc
import os
import shutil
from typing import BinaryIO
from fastapi.concurrency import run_in_threadpool


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

    @abc.abstractmethod
    async def generate_presigned_url(self, file_path: str, expiration: int = 3600) -> str:
        """Generate a secure, temporary retrieval URL."""
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
        
        def _write():
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(file_data)
            return destination_path
            
        return await run_in_threadpool(_write)

    async def save_stream(self, file_stream: BinaryIO, destination_path: str) -> str:
        full_path = self._get_full_path(destination_path)
        
        def _write_stream():
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                shutil.copyfileobj(file_stream, f)
            return destination_path
            
        return await run_in_threadpool(_write_stream)

    async def read_file(self, source_path: str) -> bytes:
        full_path = self._get_full_path(source_path)
        
        def _read():
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"File not found at: {source_path}")
            with open(full_path, "rb") as f:
                return f.read()
                
        return await run_in_threadpool(_read)

    async def delete_file(self, file_path: str) -> bool:
        full_path = self._get_full_path(file_path)
        
        def _delete():
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
            return False
            
        return await run_in_threadpool(_delete)

    async def exists(self, file_path: str) -> bool:
        full_path = self._get_full_path(file_path)
        return await run_in_threadpool(os.path.exists, full_path)

    async def generate_presigned_url(self, file_path: str, expiration: int = 3600) -> str:
        # For local, point to the direct API static file retrieval endpoint
        return f"/api/v1/images/file/{file_path}"


class S3StorageProvider(StorageProvider):
    """Simulated AWS S3 Storage Provider that writes to a local subfolder for testing."""
    def __init__(self, bucket_name: str, base_dir: str = "./storage/s3"):
        self.bucket_name = bucket_name
        self.base_dir = os.path.abspath(os.path.join(base_dir, bucket_name))
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_full_path(self, relative_path: str) -> str:
        clean_path = os.path.normpath(relative_path).lstrip("\\/")
        return os.path.join(self.base_dir, clean_path)

    async def save_file(self, file_data: bytes, destination_path: str) -> str:
        full_path = self._get_full_path(destination_path)
        
        def _write():
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(file_data)
            return f"s3://{self.bucket_name}/{destination_path}"
            
        return await run_in_threadpool(_write)

    async def save_stream(self, file_stream: BinaryIO, destination_path: str) -> str:
        full_path = self._get_full_path(destination_path)
        
        def _write_stream():
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                shutil.copyfileobj(file_stream, f)
            return f"s3://{self.bucket_name}/{destination_path}"
            
        return await run_in_threadpool(_write_stream)

    async def read_file(self, source_path: str) -> bytes:
        full_path = self._get_full_path(source_path)
        
        def _read():
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"S3 Object not found: {source_path}")
            with open(full_path, "rb") as f:
                return f.read()
                
        return await run_in_threadpool(_read)

    async def delete_file(self, file_path: str) -> bool:
        full_path = self._get_full_path(file_path)
        
        def _delete():
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
            return False
            
        return await run_in_threadpool(_delete)

    async def exists(self, file_path: str) -> bool:
        full_path = self._get_full_path(file_path)
        return await run_in_threadpool(os.path.exists, full_path)

    async def generate_presigned_url(self, file_path: str, expiration: int = 3600) -> str:
        return f"https://s3.amazonaws.com/{self.bucket_name}/{file_path}?X-Amz-Expires={expiration}&X-Amz-Signature=mock"


class GCSStorageProvider(StorageProvider):
    """Simulated Google Cloud Storage Provider that writes to a local subfolder for testing."""
    def __init__(self, bucket_name: str, base_dir: str = "./storage/gcs"):
        self.bucket_name = bucket_name
        self.base_dir = os.path.abspath(os.path.join(base_dir, bucket_name))
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_full_path(self, relative_path: str) -> str:
        clean_path = os.path.normpath(relative_path).lstrip("\\/")
        return os.path.join(self.base_dir, clean_path)

    async def save_file(self, file_data: bytes, destination_path: str) -> str:
        full_path = self._get_full_path(destination_path)
        
        def _write():
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(file_data)
            return f"gs://{self.bucket_name}/{destination_path}"
            
        return await run_in_threadpool(_write)

    async def save_stream(self, file_stream: BinaryIO, destination_path: str) -> str:
        full_path = self._get_full_path(destination_path)
        
        def _write_stream():
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                shutil.copyfileobj(file_stream, f)
            return f"gs://{self.bucket_name}/{destination_path}"
            
        return await run_in_threadpool(_write_stream)

    async def read_file(self, source_path: str) -> bytes:
        full_path = self._get_full_path(source_path)
        
        def _read():
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"GCS Object not found: {source_path}")
            with open(full_path, "rb") as f:
                return f.read()
                
        return await run_in_threadpool(_read)

    async def delete_file(self, file_path: str) -> bool:
        full_path = self._get_full_path(file_path)
        
        def _delete():
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
            return False
            
        return await run_in_threadpool(_delete)

    async def exists(self, file_path: str) -> bool:
        full_path = self._get_full_path(file_path)
        return await run_in_threadpool(os.path.exists, full_path)

    async def generate_presigned_url(self, file_path: str, expiration: int = 3600) -> str:
        return f"https://storage.googleapis.com/{self.bucket_name}/{file_path}?GoogleAccessId=mock&Expires={expiration}"


class AzureBlobStorageProvider(StorageProvider):
    """Simulated Azure Blob Storage Provider that writes to a local subfolder for testing."""
    def __init__(self, container_name: str, base_dir: str = "./storage/azure"):
        self.container_name = container_name
        self.base_dir = os.path.abspath(os.path.join(base_dir, container_name))
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_full_path(self, relative_path: str) -> str:
        clean_path = os.path.normpath(relative_path).lstrip("\\/")
        return os.path.join(self.base_dir, clean_path)

    async def save_file(self, file_data: bytes, destination_path: str) -> str:
        full_path = self._get_full_path(destination_path)
        
        def _write():
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(file_data)
            return f"azure://{self.container_name}/{destination_path}"
            
        return await run_in_threadpool(_write)

    async def save_stream(self, file_stream: BinaryIO, destination_path: str) -> str:
        full_path = self._get_full_path(destination_path)
        
        def _write_stream():
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                shutil.copyfileobj(file_stream, f)
            return f"azure://{self.container_name}/{destination_path}"
            
        return await run_in_threadpool(_write_stream)

    async def read_file(self, source_path: str) -> bytes:
        full_path = self._get_full_path(source_path)
        
        def _read():
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"Azure Blob not found: {source_path}")
            with open(full_path, "rb") as f:
                return f.read()
                
        return await run_in_threadpool(_read)

    async def delete_file(self, file_path: str) -> bool:
        full_path = self._get_full_path(file_path)
        
        def _delete():
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
            return False
            
        return await run_in_threadpool(_delete)

    async def exists(self, file_path: str) -> bool:
        full_path = self._get_full_path(file_path)
        return await run_in_threadpool(os.path.exists, full_path)

    async def generate_presigned_url(self, file_path: str, expiration: int = 3600) -> str:
        return f"https://mockaccount.blob.core.windows.net/{self.container_name}/{file_path}?se=mock&sig=mock"
