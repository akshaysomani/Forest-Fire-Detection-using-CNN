import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.role import Role
from app.models.detection import Detection
from app.models.alert import Alert
from app.models.incident import Incident
from app.models.analytics import ReportDefinition, ReportExecution, KPIHistory
from app.services.password_service import password_service
from app.services.dashboard_cache_service import dashboard_cache_service
from app.services.analytics.kpi_service import kpi_service
from app.services.analytics.analytics_aggregator import analytics_aggregator

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


async def test_analytics_endpoints_and_rbac(client: AsyncClient, db: AsyncSession):
    # 1. Setup roles and users
    admin_user = await create_user_with_role(db, "admin_user", "Super Admin")
    viewer_user = await create_user_with_role(db, "viewer_user", "Viewer")
    await db.commit()

    admin_headers = await get_auth_headers(client, "admin_user")
    viewer_headers = await get_auth_headers(client, "viewer_user")

    # Seed mock data
    det = Detection(
        image_path="/static/uploads/test_fire.jpg",
        filename="test_fire.jpg",
        prediction_label="fire",
        confidence=0.97,
        model_name="CNN_v1",
        model_version="1.0.0",
        is_verified_fire=True,
        alert_sent=True
    )
    db.add(det)
    await db.flush()

    alert = Alert(
        detection_id=det.id,
        severity="High",
        status="acknowledged",
        message="Test alert"
    )
    db.add(alert)
    await db.flush()

    incident = Incident(
        alert_id=alert.id,
        title="Test Incident",
        status="Resolved",
        severity="High"
    )
    db.add(incident)
    await db.commit()

    # Clear cache
    await dashboard_cache_service.clear()

    # Test GET /analytics/kpis
    res = await client.get("/api/v1/analytics/kpis", headers=viewer_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["fire_detection_count"] >= 1
    assert data["detection_accuracy"] == 1.0

    # Test GET /analytics/executive-dashboard
    res = await client.get("/api/v1/analytics/executive-dashboard", headers=viewer_headers)
    assert res.status_code == 200
    data = res.json()
    assert "fire_hazard_level" in data
    assert "active_responders_ratio" in data

    # Test POST /analytics/reports/definitions (RBAC Check)
    # Viewer tries to create -> 403
    def_data = {
        "name": "Daily Alert Summary",
        "description": "Daily counts",
        "report_type": "alerts",
        "parameters": {"start_date": "2026-06-01T00:00:00Z"},
        "schedule_cron": "0 0 * * *",
        "is_scheduled": True
    }
    res = await client.post("/api/v1/analytics/reports/definitions", json=def_data, headers=viewer_headers)
    assert res.status_code == 403

    # Admin tries to create -> 201
    res = await client.post("/api/v1/analytics/reports/definitions", json=def_data, headers=admin_headers)
    assert res.status_code == 201
    def_response = res.json()
    assert def_response["name"] == "Daily Alert Summary"
    def_id = def_response["id"]

    # Test GET /analytics/reports (list report definitions)
    res = await client.get("/api/v1/analytics/reports", headers=viewer_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # Test POST /analytics/reports/generate (adhoc run)
    gen_data = {
        "report_type": "fire_detections",
        "format": "JSON",
        "parameters": {"start_date": "2026-06-01T00:00:00Z"}
    }
    res = await client.post("/api/v1/analytics/reports/generate", json=gen_data, headers=viewer_headers)
    assert res.status_code == 200
    exec_data = res.json()
    assert exec_data["status"] == "completed"
    assert exec_data["format"] == "JSON"
    exec_id = exec_data["id"]

    # Test GET /analytics/reports/{id}
    res = await client.get(f"/api/v1/analytics/reports/{exec_id}", headers=viewer_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "completed"

    # Test GET /analytics/export
    res = await client.get(f"/api/v1/analytics/export?execution_id={exec_id}", headers=viewer_headers)
    assert res.status_code == 200
    export_content = res.json()
    assert export_content["report_type"] == "fire_detections"
    assert export_content["summary"]["total_records"] >= 1


async def test_analytics_aggregations(db: AsyncSession):
    # Test Aggregator calls
    now = datetime.now(timezone.utc)
    # Run daily aggregator
    await analytics_aggregator.aggregate_daily(db, now)
    # Run weekly aggregator
    await analytics_aggregator.aggregate_weekly(db, now)
    # Commit
    await db.commit()


async def test_kpi_service_history(db: AsyncSession):
    # Seed detection so fire_detection_count is >= 1.0
    det = Detection(
        image_path="/static/uploads/test_fire_history.jpg",
        filename="test_fire_history.jpg",
        prediction_label="fire",
        confidence=0.98,
        model_name="CNN_v1",
        model_version="1.0.0",
        is_verified_fire=True,
        alert_sent=True
    )
    db.add(det)
    await db.flush()

    # Log current KPIs to history
    kpis = await kpi_service.record_current_kpis(db)
    assert "fire_detection_count" in kpis
    assert kpis["fire_detection_count"] >= 1.0
    await db.commit()

    # Query history
    history = await kpi_service.get_historical_kpis(db, "fire_detection_count", days=7)
    assert len(history) >= 1
    assert history[0].kpi_value >= 1.0
