import uuid
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class DatasetCategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=255)


class DatasetCategoryResponse(DatasetCategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class DatasetLabelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=255)


class DatasetLabelResponse(DatasetLabelBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class DatasetBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: str | None = Field(None, max_length=500)
    tags: str | None = Field(None, max_length=512)  # Comma-separated tags


class DatasetCreate(DatasetBase):
    category_id: uuid.UUID


class DatasetUpdate(BaseModel):
    name: str | None = Field(None, min_length=3, max_length=100)
    description: str | None = Field(None, max_length=500)
    category_id: uuid.UUID | None = None
    status: str | None = Field(None, max_length=50)
    tags: str | None = Field(None, max_length=512)


class DatasetResponse(DatasetBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID
    status: str
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    category: DatasetCategoryResponse | None = None


class DatasetVersionBase(BaseModel):
    version_str: str = Field(..., min_length=2, max_length=50, pattern=r"^v\d+\.\d+\.\d+$")
    description: str | None = Field(None, max_length=500)
    metadata_json: dict | None = None


class DatasetVersionCreate(DatasetVersionBase):
    pass


class DatasetVersionResponse(DatasetVersionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    status: str
    user_id: uuid.UUID
    snapshot_path: str | None
    size_bytes: int
    file_count: int
    created_at: datetime
    updated_at: datetime


class DatasetFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    version_id: uuid.UUID | None
    file_path: str
    filename: str
    file_size: int
    mime_type: str | None
    md5_hash: str
    label_id: uuid.UUID | None
    metadata_json: dict | None
    created_at: datetime
    updated_at: datetime
    label: DatasetLabelResponse | None = None


class DatasetUploadHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    upload_type: str
    original_filename: str | None
    total_files: int
    processed_files: int
    failed_files: int
    error_details: dict | None
    created_at: datetime
    updated_at: datetime


class DatasetRollbackRequest(BaseModel):
    version_str: str = Field(..., min_length=2, max_length=50, pattern=r"^v\d+\.\d+\.\d+$")


class DatasetLabelAssignRequest(BaseModel):
    file_ids: list[uuid.UUID]
    label_id: uuid.UUID | None = None


# Paginated schemas
class PaginatedDatasets(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[DatasetResponse]


class PaginatedFiles(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[DatasetFileResponse]
