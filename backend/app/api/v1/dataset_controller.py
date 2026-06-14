import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, UploadFile, File, BackgroundTasks, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_active_user, PermissionChecker
from app.models.user import User
from app.schemas.dataset_schema import (
    DatasetCreate,
    DatasetUpdate,
    DatasetResponse,
    DatasetVersionCreate,
    DatasetVersionResponse,
    DatasetFileResponse,
    DatasetUploadHistoryResponse,
    DatasetLabelAssignRequest,
    DatasetCategoryResponse,
    DatasetLabelResponse,
    PaginatedDatasets,
    PaginatedFiles,
    DatasetRollbackRequest,
)
from app.services.dataset_service import dataset_service
from app.services.dataset_upload_service import dataset_upload_service
from app.services.upload_manager import upload_manager
from app.services.label_service import label_service
from app.services.label_manager import label_manager
from app.services.dataset_version_service import dataset_version_service
from app.services.version_manager import version_manager
from app.repositories.dataset_repository import dataset_repository, dataset_file_repository

router = APIRouter()


@router.post("", response_model=DatasetResponse, status_code=201)
async def create_dataset(
    obj_in: DatasetCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("upload_images"))
):
    """
    Create a new dataset grouping.
    Requires 'upload_images' permission (Forest Officer, Research Analyst, Super Admin).
    """
    return await dataset_service.create_dataset(db, obj_in, current_user.id)


@router.get("", response_model=PaginatedDatasets)
async def list_datasets(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_predictions")),
):
    """
    List all datasets, optionally filtered by category, status, or search query.
    Requires 'view_predictions' permission (All roles).
    """
    # Viewers can only view. Non-admins will see all datasets as it is read-only,
    # but we can filter by owner if we wanted to enforce strict privacy.
    # To be general and useful, we return all datasets.
    items = await dataset_repository.list_datasets(
        db, skip=skip, limit=limit, category_id=category_id, status=status, search_query=search
    )
    total = await dataset_repository.count_datasets(db, category_id=category_id, status=status, search_query=search)
    return {"total": total, "skip": skip, "limit": limit, "items": items}


@router.get("/categories", response_model=list[DatasetCategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_predictions"))
):
    """List all seeded dataset categories."""
    return await dataset_service.get_categories(db)


@router.get("/labels", response_model=list[DatasetLabelResponse])
async def list_labels(db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_predictions"))):
    """List all seeded dataset classification labels."""
    return await label_service.list_labels(db)


@router.get("/{id}", response_model=DatasetResponse)
async def get_dataset(
    id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_predictions"))
):
    """Retrieve details for a specific dataset ID."""
    return await dataset_service.get_dataset(db, id)


@router.put("/{id}", response_model=DatasetResponse)
async def update_dataset(
    id: uuid.UUID,
    obj_in: DatasetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("upload_images")),
):
    """Update metadata for an existing dataset."""
    return await dataset_service.update_dataset(db, id, obj_in, current_user.id)


@router.delete("/{id}", status_code=204)
async def delete_dataset(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings")),
):
    """Soft delete a dataset (Super Admin/Platform Manager only)."""
    await dataset_service.delete_dataset(db, id, current_user.id)
    return None


@router.post("/upload", response_model=DatasetFileResponse, status_code=201)
async def upload_single_file(
    dataset_id: uuid.UUID = Form(...),
    label_id: uuid.UUID | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("upload_images")),
):
    """Upload a single image to a dataset."""
    return await dataset_upload_service.upload_single_file(db, dataset_id, file, current_user.id, label_id)


@router.post("/bulk-upload", status_code=200)
async def upload_bulk_files(
    dataset_id: uuid.UUID = Form(...),
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("upload_images")),
):
    """Upload multiple images to a dataset in one request."""
    return await dataset_upload_service.upload_bulk_files(db, dataset_id, files, current_user.id)


@router.post("/zip-upload", response_model=DatasetUploadHistoryResponse, status_code=202)
async def upload_zip_dataset(
    background_tasks: BackgroundTasks,
    dataset_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("upload_images")),
):
    """Upload a ZIP containing an structured image folder layout."""
    return await dataset_upload_service.upload_zip_dataset(db, dataset_id, file, current_user.id, background_tasks)


@router.get("/uploads/{history_id}", response_model=DatasetUploadHistoryResponse)
async def get_zip_upload_status(
    history_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_predictions")),
):
    """Query progress or extraction details of a background ZIP upload."""
    return await upload_manager.get_upload_status(db, history_id)


@router.get("/{id}/files", response_model=PaginatedFiles)
async def get_dataset_files(
    id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_predictions")),
):
    """List files currently contained within a dataset."""
    items = await dataset_file_repository.get_by_dataset(db, id, skip, limit)
    total = await dataset_file_repository.count_by_dataset(db, id)
    return {"total": total, "skip": skip, "limit": limit, "items": items}


@router.get("/{id}/versions", response_model=list[DatasetVersionResponse])
async def get_dataset_versions(
    id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_predictions"))
):
    """List historical version snapshots of a dataset."""
    return await dataset_version_service.get_versions(db, id)


@router.post("/{id}/versions", response_model=DatasetVersionResponse, status_code=201)
async def create_dataset_version(
    id: uuid.UUID,
    obj_in: DatasetVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("analyze_data")),
):
    """Create an immutable version snapshot ZIP of the active files."""
    return await dataset_version_service.create_version(
        db, id, obj_in.version_str, obj_in.description, current_user.id, current_user.username
    )


@router.post("/{id}/rollback", status_code=200)
async def rollback_dataset(
    id: uuid.UUID,
    payload: DatasetRollbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("analyze_data")),
):
    """Roll back active dataset files to match a previous snapshot."""
    return await version_manager.rollback_to_version(db, id, payload.version_str, current_user.id)


@router.post("/{id}/labels", status_code=200)
async def assign_labels(
    id: uuid.UUID,
    payload: DatasetLabelAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("analyze_data")),
):
    """Assign or modify classifications for specific file IDs within a dataset."""
    count = await label_manager.assign_label_to_files(db, id, payload.file_ids, payload.label_id, current_user.id)
    return {"status": "success", "updated_count": count}
