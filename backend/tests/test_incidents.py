import pytest
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.role import Role
from app.models.incident import (
    Incident,
    ResponseTeam,
    ResponseMember,
    IncidentAssignment,
    IncidentUpdate,
    IncidentStatusHistory,
    IncidentAuditLog,
)
from app.services.password_service import password_service
from app.services.incident.sla_tracker import sla_tracker
from app.services.incident.escalation_manager import escalation_manager
from app.services.incident.incident_assignment_service import incident_assignment_service
from app.services.incident.response_team_service import response_team_service
from app.services.incident.incident_observability_service import incident_observability_service
from app.services.incident.incident_monitor import incident_monitor
from app.services.incident.response_tracking_service import response_tracking_service
from app.services.incident.incident_metrics import incident_metrics
from app.services.incident.performance_tracker import performance_tracker

pytestmark = pytest.mark.asyncio


# Helper function to generate login tokens for test users
async def get_auth_headers(client: AsyncClient, username: str) -> dict:
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": username,
            "password": "Password123!"
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# Helper to create a user and assign a specific role
async def create_user_with_role(db: AsyncSession, username: str, role_name: str) -> User:
    query = select(Role).where(Role.name == role_name)
    res = await db.execute(query)
    role = res.scalar_one()

    user = User(
        email=f"{username}@forestfire.org",
        username=username,
        hashed_password=password_service.hash_password("Password123!"),
        is_active=True,
        is_verified=True
    )
    user.roles.append(role)
    db.add(user)
    await db.flush()
    return user


async def test_sla_tracker_calculations(db: AsyncSession):
    """Verify SLATracker detects breaches based on severity and duration."""
    # Create non-breached incident
    inc_ok = Incident(
        title="Recent fire incident",
        severity="Critical",
        status="Open"
    )
    db.add(inc_ok)
    
    # Create breached incident
    inc_breached = Incident(
        title="Old unattended fire",
        severity="Critical",
        status="Open"
    )
    db.add(inc_breached)
    await db.flush()

    # Backdate inc_breached created_at to 20 minutes ago (Critical SLA is 15 minutes)
    inc_breached.created_at = datetime.now(timezone.utc) - timedelta(minutes=20)
    db.add(inc_breached)
    await db.flush()

    assert sla_tracker.is_response_sla_breached(inc_ok) is False
    assert sla_tracker.is_response_sla_breached(inc_breached) is True

    # Scan active breaches
    breaches = await sla_tracker.get_active_breaches(db)
    assert inc_breached.id in [b.id for b in breaches]
    assert inc_ok.id not in [b.id for b in breaches]


async def test_escalation_manager_rules(db: AsyncSession):
    """Verify EscalationManager escalates status and bumps severity correctly."""
    inc = Incident(
        title="SLA breach incident",
        severity="Medium",
        status="Open"
    )
    db.add(inc)
    await db.flush()

    # Escalate manually
    escalated_inc = await escalation_manager.escalate_incident(
        db=db,
        incident_id=inc.id,
        user_id=None,
        reason="Manual escalation for testing"
    )
    assert escalated_inc.status == "Escalated"
    assert escalated_inc.severity == "High"  # Medium -> High

    # Verify status history and audits
    history_res = await db.execute(
        select(IncidentStatusHistory).where(IncidentStatusHistory.incident_id == inc.id)
    )
    history = history_res.scalars().all()
    assert any(h.new_status == "Escalated" for h in history)

    audit_res = await db.execute(
        select(IncidentAuditLog).where(IncidentAuditLog.incident_id == inc.id)
    )
    audits = audit_res.scalars().all()
    assert any(a.action == "incident_escalated" for a in audits)


async def test_response_team_crud(db: AsyncSession):
    """Test response team registries, members adding, and availability toggles."""
    # Create Team
    team = await response_team_service.create_team(db, "Delta Team", "Wildfire Suppression")
    assert team.name == "Delta Team"
    assert team.status == "Active"

    # Verify name uniqueness
    with pytest.raises(Exception):
        await response_team_service.create_team(db, "Delta Team", "General Dispatch")

    # Add Member
    user = await create_user_with_role(db, "ranger_delta", "Forest Officer")
    await db.commit()

    member = await response_team_service.add_member_to_team(db, team.id, user.id, "Commander")
    assert member.team_id == team.id
    assert member.user_id == user.id
    assert member.role == "Commander"
    assert member.is_available is True

    # Set availability
    updated_member = await response_team_service.set_member_availability(db, member.id, False)
    assert updated_member.is_available is False


async def test_assignment_lifecycle(db: AsyncSession):
    """Test creating assignments, accepting dispatches, and rejecting dispatches."""
    # Setup team, user, and incident
    team = await response_team_service.create_team(db, "Alpha Dispatch", "General Dispatch")
    user = await create_user_with_role(db, "officer_alpha", "Emergency Response Officer")
    inc = Incident(title="Active fire assignment test", severity="High", status="Open")
    db.add(inc)
    await db.commit()

    # Assign
    assignment = await incident_assignment_service.assign_team(db, inc.id, team.id, user.id)
    assert assignment.status == "Pending"
    assert assignment.incident_id == inc.id
    assert assignment.team_id == team.id

    # Attempt to assign already pending team
    with pytest.raises(Exception):
        await incident_assignment_service.assign_team(db, inc.id, team.id, user.id)

    # Reject assignment
    assignment = await incident_assignment_service.reject_assignment(db, assignment.id, user.id, "Insufficient gear")
    assert assignment.status == "Rejected"

    # Re-assign
    assignment = await incident_assignment_service.assign_team(db, inc.id, team.id, user.id)
    assert assignment.status == "Pending"

    # Accept assignment
    assignment = await incident_assignment_service.accept_assignment(db, assignment.id, user.id)
    assert assignment.status == "Accepted"

    # Verify incident transitioned to Assigned
    await db.refresh(inc)
    assert inc.status == "Assigned"

    # Verify team is busy (deployed)
    await db.refresh(team)
    assert team.current_incident_id == inc.id


async def test_observability_and_metrics(db: AsyncSession):
    """Verify that observability compilers compute totals, ratios, and specialties."""
    team = await response_team_service.create_team(db, "Echo Rangers", "Wildfire Suppression")
    inc = Incident(title="Echo Incident", severity="Critical", status="Resolved")
    db.add(inc)
    await db.commit()

    # Check metrics
    kpis = await response_tracking_service.get_system_kpis(db)
    assert kpis["total_incidents"] >= 1
    assert kpis["total_teams"] >= 1

    ratios = await incident_metrics.get_active_ratios(db)
    assert "active_ratio" in ratios

    timeline = await incident_metrics.get_timeline_metrics(db)
    assert len(timeline) == 7

    specialties = await performance_tracker.get_specialty_performance(db)
    assert len(specialties) >= 1

    stats = await incident_observability_service.get_observability_metrics(db)
    assert "kpis" in stats
    assert "active_ratios" in stats


async def test_incident_rest_endpoints(client: AsyncClient, db: AsyncSession):
    """Test REST endpoints and Role-Based Access Control guards."""
    admin = await create_user_with_role(db, "inc_admin", "Super Admin")
    officer = await create_user_with_role(db, "inc_officer", "Forest Officer")
    viewer = await create_user_with_role(db, "inc_viewer", "Viewer")
    await db.commit()

    admin_headers = await get_auth_headers(client, "inc_admin")
    officer_headers = await get_auth_headers(client, "inc_officer")
    viewer_headers = await get_auth_headers(client, "inc_viewer")

    # 1. Create response team (requires manage_platform_settings)
    res_team = await client.post(
        "/api/v1/incidents/response-teams",
        json={"name": "Rescue Squad 1", "specialty": "Wildfire Suppression"},
        headers=admin_headers
    )
    assert res_team.status_code == 201
    team_id = res_team.json()["id"]

    # Forest officer fails to create team
    res_team_off = await client.post(
        "/api/v1/incidents/response-teams",
        json={"name": "Rescue Squad 2", "specialty": "General Dispatch"},
        headers=officer_headers
    )
    assert res_team_off.status_code == 403

    # 2. Add responder member
    res_mem = await client.post(
        f"/api/v1/incidents/response-teams/{team_id}/members",
        json={"user_id": str(officer.id), "role": "Commander"},
        headers=admin_headers
    )
    assert res_mem.status_code == 201
    member_id = res_mem.json()["id"]

    # Toggle member availability
    res_avail = await client.patch(
        f"/api/v1/incidents/response-teams/members/{member_id}/availability?is_available=false",
        headers=officer_headers
    )
    assert res_avail.status_code == 200
    assert res_avail.json()["is_available"] is False

    # 3. Create incident manually (Forest officer has view_alerts)
    res_inc = await client.post(
        "/api/v1/incidents",
        json={
            "title": "Smoke spotted near Ridge Line",
            "description": "Thick black smoke visible from Lookout 4",
            "severity": "High",
            "latitude": 37.7749,
            "longitude": -122.4194
        },
        headers=officer_headers
    )
    assert res_inc.status_code == 201
    inc_id = res_inc.json()["id"]

    # 4. List incidents
    res_list = await client.get("/api/v1/incidents", headers=viewer_headers)
    assert res_list.status_code == 200
    assert res_list.json()["total_count"] >= 1

    # 5. Get single incident details
    res_details = await client.get(f"/api/v1/incidents/{inc_id}", headers=viewer_headers)
    assert res_details.status_code == 200
    assert res_details.json()["title"] == "Smoke spotted near Ridge Line"

    # 6. Assign team (requires view_alerts)
    # Enable team member first to make sure team is assignable
    await client.patch(
        f"/api/v1/incidents/response-teams/members/{member_id}/availability?is_available=true",
        headers=officer_headers
    )
    res_assign = await client.post(
        f"/api/v1/incidents/{inc_id}/assign",
        json={"team_id": team_id},
        headers=officer_headers
    )
    assert res_assign.status_code == 201
    assignment_id = res_assign.json()["id"]

    # 7. Accept assignment
    res_accept = await client.post(
        f"/api/v1/incidents/assignments/{assignment_id}/accept",
        headers=officer_headers
    )
    assert res_accept.status_code == 200
    assert res_accept.json()["status"] == "Accepted"

    # Verify incident state is now Assigned
    res_details_check = await client.get(f"/api/v1/incidents/{inc_id}", headers=viewer_headers)
    assert res_details_check.json()["status"] == "Assigned"

    # 8. Post situation updates (SITREP)
    res_update = await client.post(
        f"/api/v1/incidents/{inc_id}/updates",
        json={"message": "First engine arrived on site. Setting up containment lines."},
        headers=officer_headers
    )
    assert res_update.status_code == 201
    assert res_update.json()["message"] == "First engine arrived on site. Setting up containment lines."

    # 9. Escalate manually
    res_esc = await client.patch(
        f"/api/v1/incidents/{inc_id}/escalate",
        json={"reason": "Wind speed increased. Fire spreading northeast."},
        headers=officer_headers
    )
    assert res_esc.status_code == 200
    assert res_esc.json()["status"] == "Escalated"
    assert res_esc.json()["severity"] == "Critical"  # High -> Critical

    # 10. Transition status to Resolved
    res_resolved = await client.patch(
        f"/api/v1/incidents/{inc_id}/status",
        json={"status": "Resolved", "reason": "Fire completely extinguished and checked for hotspots."},
        headers=officer_headers
    )
    assert res_resolved.status_code == 200
    assert res_resolved.json()["status"] == "Resolved"

    # 11. View statistics
    res_stats = await client.get("/api/v1/incidents/statistics", headers=viewer_headers)
    assert res_stats.status_code == 200
    assert "kpis" in res_stats.json()

    # 12. View audit logs (Super Admin only)
    res_audit = await client.get("/api/v1/incidents/history", headers=admin_headers)
    assert res_audit.status_code == 200
    assert res_audit.json()["total_count"] >= 1

    # Forest officer fails to view audit logs
    res_audit_off = await client.get("/api/v1/incidents/history", headers=officer_headers)
    assert res_audit_off.status_code == 403
