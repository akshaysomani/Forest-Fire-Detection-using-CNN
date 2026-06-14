import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user, PermissionChecker
from app.models.user import User
from app.models.training import TrainingRun, TrainingCheckpoint
from app.models.dataset import Dataset
from app.core.exceptions import EntityNotFoundException, ValidationException
from app.schemas.training_schema import (
    TrainingStartRequest,
    TrainingRunResponse,
    TrainingCheckpointResponse,
    PaginatedTrainingRuns,
)
from app.services.training import training_engine, run_manager
from app.services.training.model_config import SUPPORTED_MODELS
from app.services.training.hyperparameter_manager import hyperparameter_manager

router = APIRouter()


@router.post("/start", response_model=TrainingRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_training(
    payload: TrainingStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings")),
):
    """
    Start a CNN training run in the background.
    Requires 'manage_platform_settings' permission (Super Admin/Platform Manager).
    """
    # 1. Verify dataset exists
    dataset = await db.get(Dataset, payload.dataset_id)
    if not dataset or dataset.deleted_at is not None:
        raise EntityNotFoundException(f"Dataset with ID '{payload.dataset_id}' not found.")

    # 2. Verify model architecture is supported
    model_name = payload.model_name.lower().strip()
    if model_name not in SUPPORTED_MODELS:
        raise ValidationException(
            f"Unsupported model architecture '{payload.model_name}'. " f"Choose from: {list(SUPPORTED_MODELS.keys())}"
        )

    # 3. Validate hyperparameters (will raise ValidationException if invalid)
    try:
        hyperparameter_manager.validate_and_parse(payload.hyperparameters)
    except Exception as e:
        raise ValidationException(f"Invalid hyperparameters schema: {str(e)}")

    # 4. Check if there is already an active run on the dataset
    # We allow running multiple pipelines sequentially, but not concurrently to prevent CPU/GPU thrashing
    active_runs = run_manager.list_active_runs()
    if active_runs:
        raise ValidationException("An active training run is already in progress. Please stop or wait for it to finish.")

    # 5. Create database record
    new_run = TrainingRun(
        dataset_id=payload.dataset_id,
        status="pending",
        model_name=model_name,
        hyperparameters=payload.hyperparameters,
        user_id=current_user.id,
    )
    db.add(new_run)
    await db.commit()
    await db.refresh(new_run)

    # 6. Trigger background execution thread
    training_engine.start_training_run(
        run_id=new_run.id,
        dataset_id=payload.dataset_id,
        version_str=payload.version_str,
        model_name=model_name,
        hyperparams_dict=payload.hyperparameters,
        user_id=current_user.id,
    )

    return new_run


@router.post("/stop/{run_id}", response_model=Dict[str, str])
async def stop_training(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings")),
):
    """
    Request an active training run to stop early (gracefully at the end of the current epoch).
    Requires 'manage_platform_settings' permission.
    """
    run = await db.get(TrainingRun, run_id)
    if not run or run.deleted_at is not None:
        raise EntityNotFoundException(f"Training run with ID '{run_id}' not found.")

    if run.status not in ("running", "pending"):
        raise ValidationException(f"Training run is not active. Current status: '{run.status}'")

    # Send cancellation signal
    success = run_manager.stop_run(str(run_id))

    # If the thread was registered and active, we update status to stopped (the thread will finalize)
    if not success and run.status == "running":
        # Maybe thread died or restarted, clean up status
        run.status = "stopped"
        run.completed_at = func.now()
        await db.commit()
        return {"status": "success", "message": "Training run status reset to stopped."}

    return {"status": "success", "message": "Graceful stop signal successfully sent to the training pipeline."}


@router.post("/resume", response_model=TrainingRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def resume_training(
    run_id: uuid.UUID = Query(...),
    checkpoint_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings")),
):
    """
    Resume an interrupted or stopped training run from a specific or latest checkpoint.
    Requires 'manage_platform_settings' permission.
    """
    # 1. Fetch training run
    run = await db.get(TrainingRun, run_id)
    if not run or run.deleted_at is not None:
        raise EntityNotFoundException(f"Training run with ID '{run_id}' not found.")

    if run.status in ("running", "pending"):
        raise ValidationException(f"Training run is already active.")

    # 2. Resolve target checkpoint
    if checkpoint_id:
        checkpoint = await db.get(TrainingCheckpoint, checkpoint_id)
        if not checkpoint or checkpoint.run_id != run_id:
            raise EntityNotFoundException(f"Checkpoint with ID '{checkpoint_id}' not found for run '{run_id}'.")
    else:
        # Get latest checkpoint (max epoch)
        checkpoint_query = (
            select(TrainingCheckpoint)
            .where(TrainingCheckpoint.run_id == run_id)
            .order_by(TrainingCheckpoint.epoch.desc())
            .limit(1)
        )
        res = await db.execute(checkpoint_query)
        checkpoint = res.scalar_one_or_none()

    if not checkpoint:
        raise ValidationException(f"No checkpoint found to resume from for training run '{run_id}'.")

    # 3. Verify no other run is active
    active_runs = run_manager.list_active_runs()
    if active_runs:
        raise ValidationException("An active training run is already in progress. Please stop or wait for it to finish.")

    # 4. Prepare parameters
    run.status = "running"
    run.error_message = None
    run.started_at = func.now()
    await db.commit()
    await db.refresh(run)

    # 5. Spawning resumption in background thread
    # We pass the checkpoint's hyperparameters.
    # The training engine will load checkpoints in the thread loop.
    training_engine.start_training_run(
        run_id=run.id,
        dataset_id=run.dataset_id,
        version_str=None,  # Not recreating split, it will load loader files or reuse
        model_name=run.model_name,
        hyperparams_dict=run.hyperparameters,
        user_id=current_user.id,
    )

    return run


@router.get("/status/{run_id}", response_model=TrainingRunResponse)
async def get_training_status(
    run_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_reports"))
):
    """
    Query the status and statistics of a training run.
    Requires 'view_reports' permission (Viewer roles and above).
    """
    run = await db.get(TrainingRun, run_id)
    if not run or run.deleted_at is not None:
        raise EntityNotFoundException(f"Training run with ID '{run_id}' not found.")
    return run


@router.get("/runs", response_model=PaginatedTrainingRuns)
async def list_training_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """
    List historical and active training runs (paginated).
    Requires 'view_reports' permission.
    """
    query = (
        select(TrainingRun)
        .where(TrainingRun.deleted_at.is_(None))
        .order_by(TrainingRun.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    count_query = select(func.count()).select_from(TrainingRun).where(TrainingRun.deleted_at.is_(None))

    res = await db.execute(query)
    items = list(res.scalars().all())

    count_res = await db.execute(count_query)
    total = count_res.scalar() or 0

    return {"total": total, "skip": skip, "limit": limit, "items": items}


@router.get("/metrics/{run_id}", response_model=List[Dict[str, Any]])
async def get_training_metrics(
    run_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_reports"))
):
    """
    Retrieve epoch-by-epoch loss/accuracy values for graphing.
    Requires 'view_reports' permission.
    """
    run = await db.get(TrainingRun, run_id)
    if not run or run.deleted_at is not None:
        raise EntityNotFoundException(f"Training run with ID '{run_id}' not found.")
    return run.metrics_history or []


@router.get("/checkpoints/{run_id}", response_model=List[TrainingCheckpointResponse])
async def get_training_checkpoints(
    run_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_reports"))
):
    """
    List checkpoints produced by a training run.
    Requires 'view_reports' permission.
    """
    query = (
        select(TrainingCheckpoint)
        .where(and_(TrainingCheckpoint.run_id == run_id, TrainingCheckpoint.deleted_at.is_(None)))
        .order_by(TrainingCheckpoint.epoch.asc())
    )
    res = await db.execute(query)
    return list(res.scalars().all())
