import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_active_user, PermissionChecker
from app.models.user import User
from app.schemas.prediction_result import (
    PredictionResponse,
    SinglePredictionResult,
    PaginatedPredictions,
    PredictionStatisticsResponse,
)
from app.services.inference.prediction_service import prediction_service
from app.services.inference.prediction_history_service import prediction_history_service
from app.services.inference.batch_prediction_service import batch_prediction_service
from app.services.inference.risk_analyzer import risk_analyzer
from app.services.inference.classification_service import classification_service

router = APIRouter()


@router.post("", response_model=SinglePredictionResult, status_code=status.HTTP_201_CREATED)
async def predict_single(
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("upload_images")),
):
    """
    Upload an image to perform real-time forest fire CNN prediction.
    Requires 'upload_images' permission.
    """
    file_bytes = await file.read()

    # Run prediction and store in DB
    detection = await prediction_service.predict_and_store(
        db=db,
        file_bytes=file_bytes,
        filename=file.filename or "unknown_image.jpg",
        user_id=current_user.id,
        latitude=latitude,
        longitude=longitude,
    )
    await db.commit()
    await db.refresh(detection)

    # Re-read/format output
    # Mock probabilities list based on prediction label and confidence
    # (since we don't save full logits list to SQLite, we recreate it for the response mapping)
    if detection.prediction_label == "fire":
        probs = [1.0 - detection.confidence, detection.confidence]
    else:
        probs = [detection.confidence, 1.0 - detection.confidence]

    risk_level = risk_analyzer.analyze_risk(detection.prediction_label, detection.confidence)

    return {
        "detection": detection,
        "risk_level": risk_level,
        "probabilities": {"non-fire": probs[0], "fire": probs[1]},
        "processing_duration_seconds": 0.05,  # Approximate processing latency
    }


@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
async def predict_batch(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("upload_images")),
):
    """
    Upload multiple images for asynchronous batch prediction processing.
    Returns a unique Batch Job ID to query progress.
    Requires 'upload_images' permission.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided for batch processing.")

    # Read bytes for all files
    images_payload = []
    for f in files:
        file_bytes = await f.read()
        images_payload.append({"filename": f.filename or "unknown_image.jpg", "file_bytes": file_bytes})

    # Submit batch job
    job_id = await batch_prediction_service.submit_batch(user_id=current_user.id, images=images_payload)

    return {
        "success": True,
        "message": "Batch prediction job successfully queued.",
        "job_id": str(job_id),
        "total_images": len(files),
    }


@router.get("/batch/{job_id}", status_code=status.HTTP_200_OK)
async def get_batch_job_status(job_id: uuid.UUID, current_user: User = Depends(PermissionChecker("view_predictions"))):
    """
    Check the status and processing progress of a queued batch prediction job.
    Requires 'view_predictions' permission.
    """
    status_details = batch_prediction_service.get_batch_status(job_id)
    if not status_details:
        raise HTTPException(status_code=404, detail=f"Batch job '{job_id}' not found.")
    return status_details


@router.get("", response_model=PaginatedPredictions)
async def list_predictions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_predictions")),
):
    """
    Fetch a paginated list of historic prediction records.
    Requires 'view_predictions' permission.
    """
    items, total = await prediction_history_service.get_history(db=db, skip=skip, limit=limit)
    return {"total": total, "skip": skip, "limit": limit, "items": items}


@router.get("/history", response_model=PaginatedPredictions)
async def search_predictions_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    label: Optional[str] = Query(None, description="Filter by prediction label: 'fire' or 'non-fire'"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_predictions")),
):
    """
    Query prediction history with advanced filters (labels, confidence threshold, date ranges).
    Requires 'view_predictions' permission.
    """
    items, total = await prediction_history_service.get_history(
        db=db,
        skip=skip,
        limit=limit,
        prediction_label=label,
        min_confidence=min_confidence,
        start_date=start_date,
        end_date=end_date,
    )
    return {"total": total, "skip": skip, "limit": limit, "items": items}


@router.get("/statistics", response_model=PredictionStatisticsResponse)
async def get_predictions_statistics(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_predictions"))
):
    """
    Compile system-wide prediction stats (total volume, class ratios, average metrics).
    Requires 'view_predictions' permission.
    """
    stats = await prediction_history_service.get_statistics(db)

    # Fill average latency as a default representation
    stats["average_latency_seconds"] = 0.05
    return stats


@router.get("/{id}", response_model=PredictionResponse)
async def get_prediction_by_id(
    id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_predictions"))
):
    """
    Fetch complete record details for a specific prediction ID.
    Requires 'view_predictions' permission.
    """
    return await prediction_history_service.get_by_id(db=db, prediction_id=id)
