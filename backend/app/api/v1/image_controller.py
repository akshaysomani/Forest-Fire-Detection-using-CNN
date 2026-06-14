import uuid
import io
import mimetypes
from datetime import datetime
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_active_user, PermissionChecker
from app.models.user import User
from app.schemas.image_schema import (
    ImageResponse,
    ImageStatisticsResponse,
    PaginatedImages,
    BulkUploadResponse,
)
from app.services.image_service import image_service
from app.services.image_upload_service import image_upload_service
from app.services.storage_service import storage_service
from app.repositories.image_repository import image_storage_location_repository

router = APIRouter()


async def populate_retrieval_url(db: AsyncSession, img: Any) -> Any:
    """Helper to inject generated presigned URL into image response schema."""
    if not img:
        return img
    # Look in relation list first
    loc = None
    if hasattr(img, "storage_locations") and img.storage_locations:
        loc = next((l for l in img.storage_locations if l.is_primary), None)
    if not loc:
        loc = await image_storage_location_repository.get_primary_location(db, img.id)
    if loc:
        img.retrieval_url = await storage_service.generate_presigned_url(loc.file_key_or_path)
    return img


@router.post("/upload", response_model=ImageResponse, status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    source: str = Form(..., description="Source of the image: dataset, manual, drone, cctv, satellite"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("upload_images")),
):
    """Upload a single image and trigger EXIF metadata extraction and preprocessing."""
    img = await image_upload_service.upload_single_image(
        db=db, upload_file=file, owner_id=current_user.id, upload_source=source
    )
    await db.commit()
    return await populate_retrieval_url(db, img)


@router.post("/bulk-upload", response_model=BulkUploadResponse, status_code=201)
async def bulk_upload_images(
    files: List[UploadFile] = File(...),
    source: str = Form(..., description="Source of the images"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("upload_images")),
):
    """Upload multiple images sequentially. Succeeded files are processed; failed items report errors."""
    report = await image_upload_service.upload_bulk_images(
        db=db, upload_files=files, owner_id=current_user.id, upload_source=source
    )
    await db.commit()
    return report


@router.post("/upload-zip", status_code=202)
async def upload_zip_images(
    file: UploadFile = File(...),
    source: str = Form(..., description="Source of the images"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("upload_images")),
):
    """Upload a ZIP archive. File extraction and preprocessing run asynchronously in the background."""
    res = await image_upload_service.upload_zip_images(
        db=db, zip_file=file, owner_id=current_user.id, upload_source=source, background_tasks=background_tasks
    )
    await db.commit()
    return res


@router.get("", response_model=PaginatedImages)
async def list_images(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    owner_id: Optional[uuid.UUID] = Query(None),
    source: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Fetch a paginated list of active images, with optional source and keyword filtering."""
    images = await image_service.list_images(
        db=db, skip=skip, limit=limit, owner_id=owner_id, upload_source=source, status=status, search_query=search
    )
    total = await image_service.count_images(
        db=db, owner_id=owner_id, upload_source=source, status=status, search_query=search
    )

    # Populate pre-signed URLs
    for img in images:
        await populate_retrieval_url(db, img)

    return {"total": total, "skip": skip, "limit": limit, "items": images}


@router.get("/search", response_model=PaginatedImages)
async def advanced_search_images(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    min_width: Optional[int] = Query(None),
    max_width: Optional[int] = Query(None),
    min_height: Optional[int] = Query(None),
    max_height: Optional[int] = Query(None),
    min_lat: Optional[float] = Query(None),
    max_lat: Optional[float] = Query(None),
    min_lon: Optional[float] = Query(None),
    max_lon: Optional[float] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    camera: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Advanced metadata search, supporting spatial coordinate boxes, dimensions, capture dates, and camera make."""
    images = await image_service.advanced_search(
        db=db,
        skip=skip,
        limit=limit,
        min_width=min_width,
        max_width=max_width,
        min_height=min_height,
        max_height=max_height,
        min_latitude=min_lat,
        max_latitude=max_lat,
        min_longitude=min_lon,
        max_longitude=max_lon,
        start_date=start_date,
        end_date=end_date,
        camera_model=camera,
        upload_source=source,
        status=status,
    )
    total = await image_service.count_advanced_search(
        db=db,
        min_width=min_width,
        max_width=max_width,
        min_height=min_height,
        max_height=max_height,
        min_latitude=min_lat,
        max_latitude=max_lat,
        min_longitude=min_lon,
        max_longitude=max_lon,
        start_date=start_date,
        end_date=end_date,
        camera_model=camera,
        upload_source=source,
        status=status,
    )

    for img in images:
        await populate_retrieval_url(db, img)

    return {"total": total, "skip": skip, "limit": limit, "items": images}


@router.get("/statistics", response_model=ImageStatisticsResponse)
async def get_statistics(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """Retrieve system-wide aggregated storage statistics and source metrics."""
    return await image_service.get_statistics(db)


@router.get("/{id}", response_model=ImageResponse)
async def get_image(id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """Fetch full relational properties and versions of a specific image."""
    img = await image_service.get_image(db, id)
    # Log access audit record
    await image_service.log_access(db=db, image_id=img.id, user_id=current_user.id, access_type="read")
    await db.commit()
    return await populate_retrieval_url(db, img)


@router.delete("/{id}", status_code=204)
async def delete_image(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings")),
):
    """Soft-delete an image record and log the cleanup action in the audit logs."""
    await image_service.delete_image(db, id, user_id=current_user.id)
    await db.commit()


@router.get("/file/{file_path:path}", response_class=StreamingResponse)
async def get_local_file(
    file_path: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Read local storage bytes and stream them to authorized HTTP clients."""
    try:
        file_bytes = await storage_service.read_file(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        return StreamingResponse(io.BytesIO(file_bytes), media_type=mime_type or "application/octet-stream")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found in local storage.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")
