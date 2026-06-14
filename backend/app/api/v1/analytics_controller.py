import uuid
import os
from typing import List
from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_active_user, PermissionChecker
from app.models.user import User
from app.schemas.analytics_schema import (
    KPISummaryResponse,
    TrendResponse,
    TrendItem,
    ReportDefinitionCreate,
    ReportDefinitionResponse,
    ReportExecutionResponse,
    ReportGenerateRequest,
    ExecutiveDashboardResponse,
)
from app.services.analytics.kpi_service import kpi_service
from app.services.analytics.trend_engine import trend_engine
from app.services.analytics.reporting_service import reporting_service
from app.services.analytics.executive_dashboard_service import executive_dashboard_service
from app.services.storage_service import storage_service
from app.core.exceptions import AnalyticsException

router = APIRouter()


@router.get("/kpis", response_model=KPISummaryResponse)
async def get_kpis(
    bypass_cache: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """Retrieve real-time computed key performance indicators (KPIs)."""
    kpi_data = await kpi_service.get_current_kpi_summary(db, bypass_cache=bypass_cache)
    return kpi_data


@router.get("/trends", response_model=TrendResponse)
async def get_trends(
    kpi_name: str = Query(...),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """Retrieve historical time-series metric snapshots for plotting trend graphs."""
    history = await kpi_service.get_historical_kpis(db, kpi_name=kpi_name, days=days)

    # Map to schemas
    trend_items = [TrendItem(date_bucket=item.recorded_date.strftime("%Y-%m-%d"), value=item.kpi_value) for item in history]
    return TrendResponse(kpi_name=kpi_name, trends=trend_items)


@router.get("/reports", response_model=List[ReportDefinitionResponse])
async def list_report_definitions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """List all saved report templates/definitions configurations."""
    return await reporting_service.get_definitions(db, skip=skip, limit=limit)


@router.post("/reports/definitions", response_model=ReportDefinitionResponse, status_code=status.HTTP_201_CREATED)
async def create_report_definition(
    data: ReportDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings")),
):
    """Create a new reporting template definition (Requires Admin)."""
    return await reporting_service.create_definition(db, data, current_user.id)


@router.post("/reports/generate", response_model=ReportExecutionResponse)
async def generate_report_adhoc(
    request: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """Trigger an ad-hoc report compilation and export job."""
    return await reporting_service.generate_report(
        db=db,
        report_type=request.report_type,
        export_format=request.format,
        parameters=request.parameters,
        user_id=current_user.id,
    )


@router.get("/reports/{id}", response_model=ReportExecutionResponse)
async def get_report_execution(
    id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_reports"))
):
    """Fetch status or download path details for a specific report execution run."""
    return await reporting_service.get_execution(db, id)


@router.get("/export")
async def download_report_export(
    execution_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """Download the completed export file (PDF, CSV, Excel, or JSON) directly."""
    execution = await reporting_service.get_execution(db, execution_id)
    if execution.status != "completed":
        raise AnalyticsException(f"Report execution has status '{execution.status}' and cannot be downloaded.")

    if not execution.file_path:
        raise AnalyticsException("Report execution is missing a generated file path.")

    # Read binary bytes programmatically (provider agnostic)
    file_bytes = await storage_service.read_file(execution.file_path)

    mime_types = {
        "PDF": "application/pdf",
        "CSV": "text/csv",
        "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "JSON": "application/json",
    }
    media_type = mime_types.get(execution.format, "application/octet-stream")
    filename = os.path.basename(execution.file_path)

    return Response(
        content=file_bytes, media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/executive-dashboard", response_model=ExecutiveDashboardResponse)
async def get_executive_dashboard(
    bypass_cache: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """Retrieve strategic executive dashboards indicators."""
    return await executive_dashboard_service.get_executive_summary(db, bypass_cache=bypass_cache)
