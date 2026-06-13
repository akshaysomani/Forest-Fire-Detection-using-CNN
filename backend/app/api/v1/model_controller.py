import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, PermissionChecker
from app.models.user import User
from app.core.exceptions import EntityNotFoundException, ValidationException
from app.schemas.model_registry_schema import (
    ModelCreateRequest,
    ModelResponse,
    ModelVersionCreateRequest,
    ModelVersionResponse,
    ModelVersionDetailResponse,
    ApprovalRequestCreate,
    ApprovalReviewRequest,
    ModelApprovalResponse,
    ModelDeploymentRequest,
    ModelDeploymentResponse,
    ModelRollbackRequest,
    ModelVersionCompareResponse,
    ModelLifecycleEventResponse,
    ModelArtifactResponse,
    PaginatedModels
)
from app.services.model_registry.model_registry_service import model_registry_service
from app.services.model_registry.model_lifecycle_service import model_lifecycle_service
from app.services.model_registry.approval_service import approval_service
from app.services.model_registry.deployment_tracking_service import deployment_tracking_service
from app.services.model_registry.model_repository import model_repository
from app.services.model_registry.artifact_repository import artifact_repository
from app.models.model_registry import (
    RegisteredModel,
    ModelVersion,
    ModelDeployment,
    ModelApproval,
    ModelLifecycleEvent,
    ModelArtifact
)

router = APIRouter()


@router.post("", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model_family(
    payload: ModelCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings"))
):
    """
    Register a new model definition family.
    Requires 'manage_platform_settings' permission.
    """
    return await model_registry_service.register_model(
        db=db,
        name=payload.name,
        description=payload.description,
        user_id=current_user.id
    )


@router.get("", response_model=PaginatedModels)
async def list_models(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports"))
):
    """
    List registered model families (paginated).
    Requires 'view_reports' permission.
    """
    models, total = await model_repository.list_models(db, skip, limit)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": models
    }


@router.get("/versions", response_model=Dict[str, Any])
async def get_model_versions(
    model_id: Optional[uuid.UUID] = Query(None),
    version_a: Optional[uuid.UUID] = Query(None, description="First version ID for comparison"),
    version_b: Optional[uuid.UUID] = Query(None, description="Second version ID for comparison"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports"))
):
    """
    If 'version_a' and 'version_b' are specified, compares metrics and hyperparameters.
    Otherwise, lists model versions for 'model_id'.
    Requires 'view_reports' permission.
    """
    if version_a and version_b:
        comparison = await model_registry_service.compare_versions(db, version_a, version_b)
        comparison["version_a"] = ModelVersionResponse.model_validate(comparison["version_a"])
        comparison["version_b"] = ModelVersionResponse.model_validate(comparison["version_b"])
        return comparison

    if not model_id:
        raise ValidationException("Must provide either both 'version_a' and 'version_b' for comparison, or 'model_id' to list versions.")

    versions, total = await model_repository.list_versions(db, model_id, skip, limit)
    versions_pydantic = [ModelVersionResponse.model_validate(v) for v in versions]
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": versions_pydantic
    }


@router.get("/versions/{version_id}", response_model=ModelVersionDetailResponse)
async def get_model_version_details(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports"))
):
    """
    Get detailed information about a specific model version, including artifacts, deployments, and lifecycle history.
    Requires 'view_reports' permission.
    """
    return await model_registry_service.get_model_version_details(db, version_id)


@router.post("/versions", response_model=ModelVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_model_version(
    payload: ModelVersionCreateRequest,
    increment_type: str = Query("patch", description="patch, minor, major"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings"))
):
    """
    Register a new version of a model linked to a training run.
    Requires 'manage_platform_settings' permission.
    """
    return await model_registry_service.register_model_version(
        db=db,
        model_id=payload.model_id,
        training_run_id=payload.training_run_id,
        checkpoint_id=payload.checkpoint_id,
        description=payload.description,
        release_notes=payload.release_notes,
        user_id=current_user.id,
        increment_type=increment_type
    )





@router.post("/approve/request", response_model=ModelApprovalResponse, status_code=status.HTTP_201_CREATED)
async def create_approval_request(
    payload: ApprovalRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings"))
):
    """
    Initiate a model promotion approval request.
    Requires 'manage_platform_settings' permission.
    """
    return await approval_service.request_approval(
        db=db,
        model_version_id=payload.model_version_id,
        requested_by=current_user.id,
        target_stage=payload.target_stage,
        request_notes=payload.request_notes
    )


@router.post("/approve", response_model=ModelApprovalResponse)
async def submit_approval_review(
    payload: ApprovalReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings"))
):
    """
    Review and approve/reject a pending model promotion request.
    Requires 'manage_platform_settings' permission.
    """
    return await approval_service.review_approval(
        db=db,
        approval_id=payload.approval_id,
        reviewed_by=current_user.id,
        status=payload.status,
        review_notes=payload.review_notes
    )


@router.post("/deploy", response_model=ModelDeploymentResponse)
async def deploy_model_version(
    payload: ModelDeploymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings"))
):
    """
    Deploy a model version to staging or production.
    Requires 'manage_platform_settings' permission.
    """
    return await deployment_tracking_service.deploy_version(
        db=db,
        model_version_id=payload.model_version_id,
        environment=payload.environment,
        deployed_by=current_user.id,
        metrics=payload.metrics
    )


@router.post("/rollback", response_model=ModelDeploymentResponse)
async def rollback_deployment(
    payload: ModelRollbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings"))
):
    """
    Rollback the active deployment in an environment to the previous stable deployment.
    Requires 'manage_platform_settings' permission.
    """
    return await deployment_tracking_service.rollback_deployment(
        db=db,
        model_id=payload.model_id,
        environment=payload.environment,
        performed_by=current_user.id
    )


@router.get("/history", response_model=List[ModelLifecycleEventResponse])
async def get_lifecycle_history(
    model_version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports"))
):
    """
    List state transition lifecycle logs for a model version.
    Requires 'view_reports' permission.
    """
    return await model_lifecycle_service.get_lifecycle_history(db, model_version_id)


@router.get("/artifacts", response_model=List[ModelArtifactResponse])
async def list_artifacts(
    model_version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports"))
):
    """
    List registered artifacts for a model version.
    Requires 'view_reports' permission.
    """
    return await artifact_repository.list_artifacts_for_version(db, model_version_id)


@router.get("/observability/metrics")
async def get_observability_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports"))
):
    """
    Retrieve system observability telemetry for model registration, approvals, and deployments.
    Requires 'view_reports' permission.
    """
    from app.services.model_registry.model_observability_service import model_observability_service
    return await model_observability_service.get_metrics(db)


@router.get("/{id}", response_model=ModelResponse)
async def get_model_family(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports"))
):
    """
    Get registered model family summary.
    Requires 'view_reports' permission.
    """
    model = await model_repository.get_model(db, id)
    if not model:
        raise EntityNotFoundException(f"Model family '{id}' not found.")
    return model
