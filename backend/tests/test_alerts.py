import pytest
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.role import Role
from app.models.detection import Detection
from app.models.alert import Alert, AlertEvent, AlertNotification, AlertPreference, AlertAcknowledgement, AlertAuditLog
from app.services.password_service import password_service
from app.services.alert import (
    event_bus,
    alert_rules_service,
    severity_classifier,
    risk_score_calculator,
    alert_priority_manager,
    alert_generator,
    alert_preferences_service,
    preference_manager,
    escalation_service,
    alert_observability_service,
    queue_manager,
)

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


async def test_severity_classification():
    """Verify that severity maps correctly based on label and confidence."""
    assert severity_classifier.classify("non-fire", 0.95) == "Informational"
    assert severity_classifier.classify("fire", 0.95) == "Critical"
    assert severity_classifier.classify("fire", 0.85) == "High"
    assert severity_classifier.classify("fire", 0.70) == "Medium"
    assert severity_classifier.classify("fire", 0.55) == "Low"
    assert severity_classifier.classify("fire", 0.40) == "Informational"


async def test_risk_score_calculation():
    """Verify risk scores calculated match confidence, locations, categories."""
    # Base: fire, confidence 0.8 -> 80% * 80 points = 64 points
    # No coords, no category -> 64
    score_base = risk_score_calculator.calculate_score("fire", 0.8)
    assert score_base == 64.0

    # Non-fire -> 0.0
    assert risk_score_calculator.calculate_score("non-fire", 0.9) == 0.0

    # High-risk area coords (California approx: 35, -120) -> adds 15 points -> 64 + 15 = 79
    score_coords = risk_score_calculator.calculate_score("fire", 0.8, latitude=35.0, longitude=-120.0)
    assert score_coords == 79.0

    # Normal coords -> adds 5 points -> 64 + 5 = 69
    score_normal_coords = risk_score_calculator.calculate_score("fire", 0.8, latitude=10.0, longitude=10.0)
    assert score_normal_coords == 69.0

    # Category dry/forest/wildfire -> adds 5 points -> 64 + 5 = 69
    score_cat = risk_score_calculator.calculate_score("fire", 0.8, category="dry_forest")
    assert score_cat == 69.0


async def test_alert_rules_evaluation():
    """Verify alert rules triggering and update behavior."""
    assert alert_rules_service.should_raise_alert("fire", 0.75) is True
    assert alert_rules_service.should_raise_alert("fire", 0.65) is False
    assert alert_rules_service.should_raise_alert("non-fire", 0.95) is False

    # Update threshold to 0.60
    alert_rules_service.update_rules({"min_confidence_threshold": 0.60})
    assert alert_rules_service.should_raise_alert("fire", 0.65) is True

    # Revert threshold
    alert_rules_service.update_rules({"min_confidence_threshold": 0.70})


async def test_quiet_hours_checks(db: AsyncSession):
    """Test user quiet hours preferences parsing and logic."""
    pref = AlertPreference(
        user_id=uuid.uuid4(),
        channel="email",
        min_severity="High",
        enabled=True,
        quiet_hours_start="22:00",
        quiet_hours_end="06:00"
    )

    # Within quiet hours (cross midnight)
    assert alert_preferences_service.is_in_quiet_hours(pref, "23:30") is True
    assert alert_preferences_service.is_in_quiet_hours(pref, "02:00") is True
    # Outside quiet hours
    assert alert_preferences_service.is_in_quiet_hours(pref, "12:00") is False
    assert alert_preferences_service.is_in_quiet_hours(pref, "08:30") is False

    # Test same-day quiet hours (e.g. 09:00 to 17:00)
    pref_sameday = AlertPreference(
        user_id=uuid.uuid4(),
        channel="in_app",
        min_severity="Medium",
        enabled=True,
        quiet_hours_start="09:00",
        quiet_hours_end="17:00"
    )
    assert alert_preferences_service.is_in_quiet_hours(pref_sameday, "12:00") is True
    assert alert_preferences_service.is_in_quiet_hours(pref_sameday, "08:00") is False
    assert alert_preferences_service.is_in_quiet_hours(pref_sameday, "19:00") is False


async def test_sla_breach_detection():
    """Verify AlertPriorityManager checks response time limits."""
    # Low SLA is 120 minutes
    created_old = datetime.now(timezone.utc) - timedelta(minutes=130)
    created_recent = datetime.now(timezone.utc) - timedelta(minutes=10)

    assert alert_priority_manager.is_sla_breached("Low", created_old) is True
    assert alert_priority_manager.is_sla_breached("Low", created_recent) is False
    assert alert_priority_manager.is_sla_breached("Low", created_old, acknowledged_at=datetime.now()) is False


async def test_event_bus_and_queues():
    """Verify EventBus publishes and executes async handlers."""
    bus_received = []

    async def mock_callback(payload):
        bus_received.append(payload)

    # Start bus and subscribe
    event_bus.subscribe("test_event", mock_callback)
    event_bus.start()

    await event_bus.publish("test_event", {"hello": "world"})
    # Wait for queue worker to pick up and process
    await asyncio.sleep(0.1)

    await event_bus.stop()

    assert len(bus_received) == 1
    assert bus_received[0]["hello"] == "world"


async def test_alert_generation_from_detection(db: AsyncSession):
    """Test generating alerts from fire detection records."""
    # Setup mock user
    user = await create_user_with_role(db, "alert_officer", "Forest Officer")
    await db.commit()

    det = Detection(
        user_id=user.id,
        image_path="/static/uploads/fire.jpg",
        filename="fire.jpg",
        prediction_label="fire",
        confidence=0.88,
        model_name="CNN_v1",
        model_version="1.0",
        is_verified_fire=None,
        alert_sent=False
    )
    db.add(det)
    await db.flush()

    # Trigger evaluation
    alert = await alert_generator.evaluate_detection(db, det)
    assert alert is not None
    assert alert.detection_id == det.id
    assert alert.severity == "High"  # 0.88 confidence -> High
    assert alert.status == "active"
    assert det.alert_sent is True

    # Check that AlertEvent record is created
    res = await db.execute(select(AlertEvent).where(AlertEvent.alert_id == alert.id))
    event_log = res.scalar_one_or_none()
    assert event_log is not None
    assert event_log.event_type == "fire_prediction"
    assert event_log.payload["prediction_label"] == "fire"


async def test_escalation_service_sla(db: AsyncSession):
    """Test that EscalationService escalates breached alerts."""
    # Create manual alert that has breached SLA
    breached_alert = Alert(
        severity="Critical",  # SLA is 15 minutes
        status="active",
        message="Breached fire warning alert",
    )
    # Force creation time back 20 minutes
    breached_alert.created_at = datetime.now(timezone.utc) - timedelta(minutes=20)
    db.add(breached_alert)
    await db.flush()

    escalated = await escalation_service.check_and_escalate_alerts(db)
    assert len(escalated) == 1
    assert escalated[0].id == breached_alert.id
    assert escalated[0].status == "escalated"

    # Verify audit log recorded it
    res = await db.execute(select(AlertAuditLog).where(AlertAuditLog.alert_id == breached_alert.id, AlertAuditLog.action == "alert_escalated"))
    audit = res.scalar_one_or_none()
    assert audit is not None


async def test_alert_rest_endpoints(client: AsyncClient, db: AsyncSession):
    """Verify all REST API endpoint functions under RBAC controls."""
    # 1. Setup users with appropriate roles
    admin = await create_user_with_role(db, "alert_admin", "Super Admin")
    officer = await create_user_with_role(db, "alert_officer_two", "Forest Officer")
    viewer = await create_user_with_role(db, "alert_viewer", "Viewer")
    await db.commit()

    admin_headers = await get_auth_headers(client, "alert_admin")
    officer_headers = await get_auth_headers(client, "alert_officer_two")
    viewer_headers = await get_auth_headers(client, "alert_viewer")

    # 2. Test manual alert generation (Super Admin holds manage_platform_settings)
    res_create = await client.post(
        "/api/v1/alerts",
        json={
            "severity": "Critical",
            "message": "Manual test fire alert",
            "payload": {"source": "manual_test"}
        },
        headers=admin_headers
    )
    assert res_create.status_code == 201
    alert_id = res_create.json()["id"]

    # Forest officer attempts to generate manual alert -> 403 (does not hold manage_platform_settings)
    res_create_off = await client.post(
        "/api/v1/alerts",
        json={
            "severity": "Low",
            "message": "Fail test",
        },
        headers=officer_headers
    )
    assert res_create_off.status_code == 403

    # 3. Test list alerts (Forest officer has view_alerts permission)
    res_list = await client.get("/api/v1/alerts?severity=Critical", headers=officer_headers)
    assert res_list.status_code == 200
    assert res_list.json()["total_count"] >= 1

    # Viewer lists alerts -> 403 (Viewer does not have view_alerts permission)
    res_list_view = await client.get("/api/v1/alerts", headers=viewer_headers)
    assert res_list_view.status_code == 403

    # 4. Test get single alert details
    res_get = await client.get(f"/api/v1/alerts/{alert_id}", headers=officer_headers)
    assert res_get.status_code == 200
    assert res_get.json()["message"] == "Manual test fire alert"

    # 5. Test Acknowledge alert
    res_ack = await client.patch(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        json={"notes": "Verifying site cameras."},
        headers=officer_headers
    )
    assert res_ack.status_code == 200
    assert res_ack.json()["status"] == "acknowledged"

    # 6. Test Resolve alert
    res_res = await client.patch(
        f"/api/v1/alerts/{alert_id}/resolve",
        json={"notes": "Controlled burn resolved."},
        headers=officer_headers
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "resolved"

    # 7. Test get statistics (observability)
    res_stats = await client.get("/api/v1/alerts/statistics", headers=officer_headers)
    assert res_stats.status_code == 200
    assert "active_alerts" in res_stats.json()
    assert "average_acknowledgement_time_seconds" in res_stats.json()

    # 8. Test get & update user preferences (requires authenticated context, so Viewer works)
    res_pref = await client.get("/api/v1/alerts/preferences", headers=viewer_headers)
    assert res_pref.status_code == 200
    assert len(res_pref.json()) >= 2  # defaults initialized

    res_pref_put = await client.put(
        "/api/v1/alerts/preferences",
        json=[
            {
                "channel": "email",
                "min_severity": "Critical",
                "enabled": False,
                "quiet_hours_start": "23:00",
                "quiet_hours_end": "05:00"
            }
        ],
        headers=viewer_headers
    )
    assert res_pref_put.status_code == 200
    # Find email channel in update results
    email_pref = [p for p in res_pref_put.json() if p["channel"] == "email"][0]
    assert email_pref["enabled"] is False
    assert email_pref["min_severity"] == "Critical"
    assert email_pref["quiet_hours_start"] == "23:00"

    # 9. Test list audit history (Super Admin has access_audit_logs)
    res_audit = await client.get("/api/v1/alerts/history", headers=admin_headers)
    assert res_audit.status_code == 200
    assert res_audit.json()["total_count"] >= 1

    # Officer lists audit history -> 403 (no access_audit_logs permission)
    res_audit_off = await client.get("/api/v1/alerts/history", headers=officer_headers)
    assert res_audit_off.status_code == 403
