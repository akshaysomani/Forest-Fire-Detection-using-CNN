import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_active_user, PermissionChecker
from app.models.user import User
from app.schemas.incident_schema import (
    IncidentResponse,
    IncidentDetailsResponse,
    IncidentHistoryResponse,
    ManualIncidentCreateRequest,
    IncidentStatusTransitionRequest,
    IncidentEscalationRequest,
    IncidentAssignmentResponse,
    IncidentAssignmentCreateRequest,
    IncidentAssignmentRejectRequest,
    IncidentUpdateResponse,
    IncidentUpdateCreateRequest,
    ResponseTeamResponse,
    ResponseTeamDetailsResponse,
    ResponseTeamCreateRequest,
    ResponseMemberResponse,
    ResponseMemberCreateRequest,
    IncidentAuditHistoryResponse,
)
from app.repositories.incident_repository import incident_repository
from app.services.incident.incident_service import incident_service
from app.services.incident.incident_lifecycle_service import incident_lifecycle_service
from app.services.incident.incident_assignment_service import incident_assignment_service
from app.services.incident.response_team_service import response_team_service
from app.services.incident.escalation_manager import escalation_manager
from app.services.incident.incident_observability_service import incident_observability_service
from app.services.incident.incident_monitor import incident_monitor

router = APIRouter()


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_manual_incident(
    body: ManualIncidentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_alerts")),
):
    """
    Manually report a new incident.
    Requires 'view_alerts' permission (held by dispatcher and officers).
    """
    incident = await incident_service.create_manual_incident(db=db, data=body.model_dump(), user_id=current_user.id)
    await db.commit()
    await db.refresh(incident)
    incident_monitor.increment("total_incidents_created")
    return incident


@router.get("", response_model=IncidentHistoryResponse)
async def list_incidents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_reports")),
):
    """
    List and filter incidents.
    Requires 'view_reports' permission.
    """
    items, total = await incident_repository.get_incidents_filtered(
        db=db, skip=skip, limit=limit, status=status, severity=severity, start_date=start_date, end_date=end_date
    )
    return {"incidents": items, "total_count": total}


@router.get("/history", response_model=IncidentAuditHistoryResponse)
async def list_incident_audit_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    incident_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("access_audit_logs")),
):
    """
    Retrieve security audit trail logs for incident activities.
    Requires 'access_audit_logs' permission.
    """
    items, total = await incident_repository.get_audit_history(db=db, skip=skip, limit=limit, incident_id=incident_id)
    return {"logs": items, "total_count": total}


@router.get("/statistics")
async def get_incident_statistics(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_reports"))
):
    """
    Fetch system-wide incident statistics and response team performance trends.
    Requires 'view_reports' permission.
    """
    return await incident_observability_service.get_observability_metrics(db)


@router.get("/response-teams", response_model=List[ResponseTeamDetailsResponse])
async def list_response_teams(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_alerts"))
):
    """
    List registered emergency response teams.
    Requires 'view_alerts' permission.
    """
    return await response_team_service.list_teams(db)


@router.post("/response-teams", response_model=ResponseTeamResponse, status_code=status.HTTP_201_CREATED)
async def create_response_team(
    body: ResponseTeamCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings")),
):
    """
    Register a new emergency response team.
    Requires 'manage_platform_settings' permission.
    """
    team = await response_team_service.create_team(db=db, name=body.name, specialty=body.specialty)
    await db.commit()
    await db.refresh(team)
    return team


@router.post("/response-teams/{id}/members", response_model=ResponseMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_response_member(
    id: uuid.UUID,
    body: ResponseMemberCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("manage_platform_settings")),
):
    """
    Add a responder member user to a response team.
    Requires 'manage_platform_settings' permission.
    """
    member = await response_team_service.add_member_to_team(db=db, team_id=id, user_id=body.user_id, role=body.role)
    await db.commit()
    await db.refresh(member)
    return member


@router.patch("/response-teams/members/{id}/availability", response_model=ResponseMemberResponse)
async def set_member_availability(
    id: uuid.UUID,
    is_available: bool = Query(..., description="Toggle availability status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_alerts")),
):
    """
    Toggle availability for a response team member.
    Requires 'view_alerts' permission.
    """
    member = await response_team_service.set_member_availability(db=db, member_id=id, is_available=is_available)
    await db.commit()
    await db.refresh(member)
    return member


@router.get("/{id}", response_model=IncidentDetailsResponse)
async def get_incident_by_id(
    id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(PermissionChecker("view_reports"))
):
    """
    Get detailed information for a single incident.
    Requires 'view_reports' permission.
    """
    incident = await incident_repository.get_incident_with_details(db, id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return incident


@router.patch("/{id}/status", response_model=IncidentResponse)
async def transition_incident_status(
    id: uuid.UUID,
    body: IncidentStatusTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_alerts")),
):
    """
    Transitions the incident lifecycle state.
    Requires 'view_alerts' permission.
    """
    incident = await incident_lifecycle_service.transition_status(
        db=db, incident_id=id, new_status=body.status, user_id=current_user.id, reason=body.reason
    )
    await db.commit()
    await db.refresh(incident)
    return incident


@router.patch("/{id}/escalate", response_model=IncidentResponse)
async def escalate_incident_manually(
    id: uuid.UUID,
    body: IncidentEscalationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_alerts")),
):
    """
    Forces manual escalation of an incident, raising priority level.
    Requires 'view_alerts' permission.
    """
    incident = await escalation_manager.escalate_incident(db=db, incident_id=id, user_id=current_user.id, reason=body.reason)
    await db.commit()
    await db.refresh(incident)
    incident_monitor.increment("total_escalations")
    return incident


@router.post("/{id}/assign", response_model=IncidentAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def assign_response_team(
    id: uuid.UUID,
    body: IncidentAssignmentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_alerts")),
):
    """
    Dispatches an active response team to an active incident.
    Requires 'view_alerts' permission.
    """
    assignment = await incident_assignment_service.assign_team(
        db=db, incident_id=id, team_id=body.team_id, assigned_by=current_user.id
    )
    await db.commit()
    await db.refresh(assignment)
    return assignment


@router.post("/assignments/{assignment_id}/accept", response_model=IncidentAssignmentResponse)
async def accept_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_alerts")),
):
    """
    A response team commander/responder accepts a dispatch assignment.
    Requires 'view_alerts' permission.
    """
    assignment = await incident_assignment_service.accept_assignment(
        db=db, assignment_id=assignment_id, user_id=current_user.id
    )
    await db.commit()
    await db.refresh(assignment)
    return assignment


@router.post("/assignments/{assignment_id}/reject", response_model=IncidentAssignmentResponse)
async def reject_assignment(
    assignment_id: uuid.UUID,
    body: IncidentAssignmentRejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_alerts")),
):
    """
    A response team rejects a dispatch assignment.
    Requires 'view_alerts' permission.
    """
    assignment = await incident_assignment_service.reject_assignment(
        db=db, assignment_id=assignment_id, user_id=current_user.id, reason=body.reason
    )
    await db.commit()
    await db.refresh(assignment)
    return assignment


@router.post("/{id}/updates", response_model=IncidentUpdateResponse, status_code=status.HTTP_201_CREATED)
async def add_incident_update(
    id: uuid.UUID,
    body: IncidentUpdateCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(PermissionChecker("view_alerts")),
):
    """
    Write a sitrep / status update message log on an incident.
    Requires 'view_alerts' permission.
    """
    from app.models.incident import IncidentUpdate, IncidentEvent, IncidentAuditLog

    # Verify incident exists
    incident = await incident_service.get_incident_by_id(db, id)

    update = IncidentUpdate(incident_id=id, user_id=current_user.id, message=body.message, media_path=body.media_path)
    db.add(update)
    await db.flush()

    event = IncidentEvent(
        incident_id=id,
        event_type="incident_updated",
        payload={"user_id": str(current_user.id), "message_snippet": body.message[:50]},
    )
    db.add(event)

    audit = IncidentAuditLog(
        incident_id=id, user_id=current_user.id, action="incident_update_created", details={"update_id": str(update.id)}
    )
    db.add(audit)

    await db.commit()
    await db.refresh(update)
    return update
