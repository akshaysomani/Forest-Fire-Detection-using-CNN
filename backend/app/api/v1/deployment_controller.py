import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, PermissionChecker
from app.models.user import User
from app.core.exceptions import EntityNotFoundException, ValidationException
from app.schemas.mlops_schema import (
    ReleaseResponse,
    ReleaseCreateRequest,
    EnvironmentResponse,
    EnvironmentCreateRequest,
    DeploymentCreateRequest,
    DeploymentPromoteRequest,
    DeploymentRollbackRequest,
    DeploymentJobResponse,
    DeploymentObservabilityResponse,
)
from app.services.mlops.model_deployment_service import model_deployment_service
from app.services.mlops.promotion_manager import promotion_manager
from app.services.mlops.environment_registry import environment_registry
from app.services.mlops.release_registry import release_registry
from app.services.mlops.deployment_orchestrator import deployment_orchestrator
from app.services.mlops.deployment_observability_service import deployment_observability_service
from app.models.mlops import DeploymentJob

router = APIRouter()


@router.post("", response_model=DeploymentJobResponse, status_code=status.HTTP_201_CREATED)
async def trigger_deployment(
    payload: DeploymentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings")),
):
    """
    Triggers a new deployment job on a target environment.
    Requires 'manage_platform_settings' permission.
    """
    return await model_deployment_service.deploy_to_environment(
        db=db, environment_id=payload.environment_id, model_version_id=payload.model_version_id, deployed_by=current_user.id
    )


@router.post("/promote", response_model=DeploymentJobResponse)
async def promote_deployment(
    payload: DeploymentPromoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings")),
):
    """
    Promotes a successful deployment to another environment.
    Requires 'manage_platform_settings' permission.
    """
    return await promotion_manager.promote_deployment(
        db=db,
        deployment_job_id=payload.deployment_job_id,
        target_environment_id=payload.target_environment_id,
        promoted_by=current_user.id,
    )


@router.post("/rollback", response_model=DeploymentJobResponse)
async def rollback_deployment(
    payload: DeploymentRollbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings")),
):
    """
    Rolls back an environment to the previous stable release configuration.
    Requires 'manage_platform_settings' permission.
    """
    return await model_deployment_service.rollback_environment(
        db=db, environment_id=payload.environment_id, performed_by=current_user.id
    )


@router.get("", response_model=List[DeploymentJobResponse])
async def list_deployments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """
    Lists current active deployment jobs.
    Requires 'view_reports' permission.
    """
    query = (
        select(DeploymentJob)
        .where(and_(DeploymentJob.status == "succeeded", DeploymentJob.deleted_at.is_(None)))
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(query)
    return list(res.scalars().all())


@router.get("/history", response_model=List[DeploymentJobResponse])
async def get_deployment_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """
    Lists previous deployment job execution histories.
    Requires 'view_reports' permission.
    """
    query = (
        select(DeploymentJob)
        .where(DeploymentJob.deleted_at.is_(None))
        .order_by(desc(DeploymentJob.created_at))
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(query)
    return list(res.scalars().all())


@router.get("/releases", response_model=List[ReleaseResponse])
async def get_releases(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """
    Lists release audits logs.
    Requires 'view_reports' permission.
    """
    releases, _ = await release_registry.list_releases(db, skip, limit)
    return releases


@router.get("/environments", response_model=List[EnvironmentResponse])
async def get_environments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """
    Lists environments and their health profiles.
    Requires 'view_reports' permission.
    """
    envs, _ = await environment_registry.list_environments(db, skip, limit)
    return envs


@router.get("/observability/metrics", response_model=DeploymentObservabilityResponse)
async def get_observability_metrics(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_reports"))
):
    """
    Exposes real-time deployment metrics.
    Requires 'view_reports' permission.
    """
    metrics = await deployment_observability_service.get_metrics_summary(db)
    return metrics
