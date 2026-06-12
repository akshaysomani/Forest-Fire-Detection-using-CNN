import uuid
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any


class ImageMetadataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_id: uuid.UUID
    width: int
    height: int
    exif_data: dict | None = None
    gps_latitude: float | None = None
    gps_longitude: float | None = None
    captured_at: datetime | None = None
    camera_make: str | None = None
    camera_model: str | None = None
    extra_metadata: dict | None = None


class ImageVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_id: uuid.UUID
    version_number: int
    purpose: str
    file_path: str
    size_bytes: int
    md5_hash: str


class ImageStorageLocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_id: uuid.UUID
    image_version_id: uuid.UUID | None = None
    provider: str
    bucket_or_container: str
    file_key_or_path: str
    is_primary: bool


class ImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    original_filename: str
    mime_type: str | None = None
    size_bytes: int
    md5_hash: str
    owner_id: uuid.UUID
    upload_source: str
    status: str
    created_at: datetime
    updated_at: datetime
    metadata_relation: ImageMetadataResponse | None = None
    versions: list[ImageVersionResponse] = []
    storage_locations: list[ImageStorageLocationResponse] = []
    retrieval_url: str | None = None


class ImageUploadResponse(BaseModel):
    id: uuid.UUID
    filename: str
    md5_hash: str
    size_bytes: int
    status: str
    upload_source: str


class BulkUploadResponse(BaseModel):
    total: int
    success_count: int
    failed_count: int
    success_images: list[ImageUploadResponse]
    failed_images: list[dict]


class PaginatedImages(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[ImageResponse]


class ImageStatisticsResponse(BaseModel):
    total_count: int
    total_size_bytes: int
    source_breakdown: dict
    status_breakdown: dict
