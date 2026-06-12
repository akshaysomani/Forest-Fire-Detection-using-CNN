from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_active_user, PermissionChecker
from app.models.user import User
from app.schemas.dashboard_schema import (
    DashboardOverviewResponse,
    DashboardStatisticsResponse,
    RecentActivityResponse,
    SystemSummaryResponse,
    UserSummaryResponse
)
from app.services.dashboard_service import dashboard_service
from app.services.monitoring_service import monitoring_service
from app.services.activity_service import activity_service

router = APIRouter()


@router.get("/overview", response_model=DashboardOverviewResponse)
async def get_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve high-level dashboard overview metrics based on user role.
    Requires 'view_reports' permission.
    """
    checker = PermissionChecker("view_reports")
    await checker(current_user, db)
    return await dashboard_service.get_overview(db, current_user)


@router.get("/statistics", response_model=DashboardStatisticsResponse)
async def get_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve detailed model confidence statistics and detection counters.
    Requires 'view_reports' permission.
    """
    checker = PermissionChecker("view_reports")
    await checker(current_user, db)
    return await dashboard_service.get_statistics(db, current_user)


@router.get("/recent-activity", response_model=RecentActivityResponse)
async def get_recent_activity(
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("access_audit_logs"))
):
    """
    Retrieve a paginated history of platform activities.
    Requires 'access_audit_logs' permission (Super Admin).
    """
    activities = await activity_service.get_recent_activities(db, skip=skip, limit=limit)
    total_count = await activity_service.get_activity_count(db)
    
    # Map model attributes to response schemas
    activity_items = []
    for act in activities:
        # Resolve username dynamically if missing
        username = None
        if act.user:
            username = act.user.username
            
        activity_items.append({
            "id": act.id,
            "user_id": act.user_id,
            "username": username,
            "action": act.action,
            "resource_type": act.resource_type,
            "resource_id": act.resource_id,
            "ip_address": act.ip_address,
            "details": act.details,
            "created_at": act.created_at
        })
        
    return {
        "activities": activity_items,
        "total_count": total_count
    }


@router.get("/system-summary", response_model=SystemSummaryResponse)
async def get_system_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings"))
):
    """
    Retrieve hardware metrics, database connection, storage usage, and active sessions.
    Requires 'manage_platform_settings' permission (Super Admin).
    """
    return await monitoring_service.get_system_summary(db)


@router.get("/user-summary", response_model=UserSummaryResponse)
async def get_user_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_users"))
):
    """
    Retrieve platform user counts, verification levels, role distributions, and growth curves.
    Requires 'manage_users' permission (Super Admin).
    """
    return await dashboard_service.get_user_summary(db)
