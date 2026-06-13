import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_active_user, PermissionChecker
from app.models.user import User
from app.schemas.alert_schema import (
    AlertResponse,
    AlertDetailsResponse,
    AlertHistoryResponse,
    AlertPreferenceResponse,
    AlertPreferenceUpdate,
    AlertAcknowledgeRequest,
    AlertResolveRequest,
    ManualAlertCreateRequest,
    AlertAuditHistoryResponse,
)
from app.repositories.alert_repository import alert_repository
from app.services.alert import (
    alert_engine,
    alert_acknowledgement_service,
    resolution_manager,
    alert_preferences_service,
    alert_observability_service,
)

router = APIRouter()


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_manual_alert(
    body: ManualAlertCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings"))
):
    """
    Manually generate a fire detection alert.
    Requires 'manage_platform_settings' permission.
    """
    alert = await alert_engine.trigger_detection_alert(
        db=db,
        detection_id=body.detection_id,
        severity=body.severity,
        message=body.message,
        payload=body.payload or {}
    )
    await db.commit()
    await db.refresh(alert)
    return alert


@router.get("", response_model=AlertHistoryResponse)
async def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by status (active, acknowledged, resolved, escalated)"),
    severity: Optional[str] = Query(None, description="Filter by severity (Critical, High, Medium, Low, Informational)"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_alerts"))
):
    """
    List and filter active or resolved fire alerts.
    Requires 'view_alerts' permission.
    """
    items, total = await alert_repository.get_alerts_filtered(
        db=db,
        skip=skip,
        limit=limit,
        status=status,
        severity=severity,
        start_date=start_date,
        end_date=end_date
    )
    return {
        "alerts": items,
        "total_count": total
    }


@router.get("/history", response_model=AlertAuditHistoryResponse)
async def list_alert_audit_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    alert_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("access_audit_logs"))
):
    """
    Retrieve security audit trail logs for alert updates and deliveries.
    Requires 'access_audit_logs' permission.
    """
    items, total = await alert_repository.get_audit_history(
        db=db,
        skip=skip,
        limit=limit,
        alert_id=alert_id
    )
    return {
        "logs": items,
        "total_count": total
    }


@router.get("/statistics")
async def get_alert_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_alerts"))
):
    """
    Fetch system-wide alert statistics, SLA speeds, and notifications telemetry.
    Requires 'view_alerts' permission.
    """
    return await alert_observability_service.get_observability_metrics(db)


@router.get("/preferences", response_model=List[AlertPreferenceResponse])
async def get_my_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Fetch current user alert delivery channels and quiet hours preferences.
    Requires authenticated user context.
    """
    return await alert_preferences_service.get_user_preferences(db, current_user.id)


@router.put("/preferences", response_model=List[AlertPreferenceResponse])
async def update_my_preferences(
    body: List[AlertPreferenceUpdate],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update my notification channels, minimum severity trigger, or quiet hours.
    Requires authenticated user context.
    """
    # Convert body schemas to dict list for service processing
    updates = [item.model_dump() for item in body]
    prefs = await alert_preferences_service.update_user_preferences(db, current_user.id, updates)
    await db.commit()
    for pref in prefs:
        await db.refresh(pref)
    return prefs


@router.get("/{id}", response_model=AlertDetailsResponse)
async def get_alert_by_id(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_alerts"))
):
    """
    Get detailed information for a single alert, including notifications and event triggers.
    Requires 'view_alerts' permission.
    """
    alert = await alert_repository.get_alert_with_details(db, id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return alert


@router.patch("/{id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    id: uuid.UUID,
    body: AlertAcknowledgeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_alerts"))
):
    """
    Acknowledge an active alert.
    Requires 'view_alerts' permission.
    """
    alert = await alert_acknowledgement_service.acknowledge_alert(
        db=db,
        alert_id=id,
        user_id=current_user.id,
        notes=body.notes
    )
    await db.commit()
    await db.refresh(alert)
    return alert


@router.patch("/{id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    id: uuid.UUID,
    body: AlertResolveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_alerts"))
):
    """
    Mark an alert as resolved.
    Requires 'view_alerts' permission.
    """
    alert = await resolution_manager.resolve_alert(
        db=db,
        alert_id=id,
        user_id=current_user.id,
        notes=body.notes
    )
    await db.commit()
    await db.refresh(alert)
    return alert
