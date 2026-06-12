import pytest
import uuid
import asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.role import Role
from app.models.detection import Detection
from app.services.password_service import password_service
from app.services.dashboard_cache_service import dashboard_cache_service
from app.services.system_metrics import system_metrics
from app.services.health_service import health_service

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


async def test_dashboard_endpoints_and_rbac(client: AsyncClient, db: AsyncSession):
    # 1. Create a Super Admin, Forest Officer, Emergency Response Officer, Research Analyst, and a regular Viewer
    admin_user = await create_user_with_role(db, "admin", "Super Admin")
    officer = await create_user_with_role(db, "officer_bob", "Forest Officer")
    emergency = await create_user_with_role(db, "emergency_alice", "Emergency Response Officer")
    analyst = await create_user_with_role(db, "analyst_charlie", "Research Analyst")
    viewer = await create_user_with_role(db, "viewer_dave", "Viewer")
    await db.commit()

    # 2. Get tokens for Admin and other roles
    admin_headers = await get_auth_headers(client, "admin")
    officer_headers = await get_auth_headers(client, "officer_bob")
    emergency_headers = await get_auth_headers(client, "emergency_alice")
    analyst_headers = await get_auth_headers(client, "analyst_charlie")
    viewer_headers = await get_auth_headers(client, "viewer_dave")

    # 3. Seed some mock detections
    det1 = Detection(
        user_id=officer.id,
        image_path="/static/uploads/fire1.jpg",
        filename="fire1.jpg",
        prediction_label="fire",
        confidence=0.965,
        model_name="CNN_ResNet50_v1",
        model_version="1.0.0",
        is_verified_fire=True,
        alert_sent=True,
        latitude=34.0522,
        longitude=-118.2437
    )
    det2 = Detection(
        user_id=officer.id,
        image_path="/static/uploads/nofire1.jpg",
        filename="nofire1.jpg",
        prediction_label="non-fire",
        confidence=0.982,
        model_name="CNN_ResNet50_v1",
        model_version="1.0.0",
        is_verified_fire=False,
        alert_sent=False,
        latitude=34.0522,
        longitude=-118.2437
    )
    det3 = Detection(
        user_id=None,  # System uploaded / anonymous
        image_path="/static/uploads/fire_false.jpg",
        filename="fire_false.jpg",
        prediction_label="fire",
        confidence=0.88,
        model_name="CNN_MobileNet_v2",
        model_version="2.1.0",
        is_verified_fire=False,  # False positive!
        alert_sent=True,
        latitude=34.0522,
        longitude=-118.2437
    )
    db.add_all([det1, det2, det3])
    await db.commit()

    # Evict cache to fetch fresh seeded values
    await dashboard_cache_service.clear()

    # --- TEST GET /dashboard/overview ---
    # Admin overview (sees total_users/active_users)
    res_admin = await client.get("/api/v1/dashboard/overview", headers=admin_headers)
    assert res_admin.status_code == 200
    data_admin = res_admin.json()
    assert data_admin["total_users"] > 0
    assert data_admin["total_uploaded_images"] == 3
    assert data_admin["fire_detections"] == 2
    # Accuracy calculation: verified correct (det1 correct, det2 correct, det3 incorrect)
    # TP: det1 (fire predicted, verified fire) = 1
    # TN: det2 (non-fire predicted, verified non-fire) = 1
    # FP: det3 (fire predicted, verified non-fire) = 1
    # Accuracy: (1 + 1) / 3 = 0.6667
    assert data_admin["detection_accuracy"] == 0.6667

    # Officer overview (sees only their own uploads -> 2)
    res_off = await client.get("/api/v1/dashboard/overview", headers=officer_headers)
    assert res_off.status_code == 200
    data_off = res_off.json()
    assert data_off["total_uploaded_images"] == 2
    assert data_off["total_users"] == 0  # Hidden for non-admin
    # Accuracy for officer: det1 correct, det2 correct -> 2/2 = 1.0000
    assert data_off["detection_accuracy"] == 1.0000

    # --- TEST GET /dashboard/statistics ---
    res_stats = await client.get("/api/v1/dashboard/statistics", headers=admin_headers)
    assert res_stats.status_code == 200
    data_stats = res_stats.json()
    assert len(data_stats["model_usage_statistics"]) >= 2
    assert data_stats["average_confidence"] > 0.9

    # --- TEST GET /dashboard/recent-activity ---
    # Admin accesses recent activities (Super Admin only)
    res_act = await client.get("/api/v1/dashboard/recent-activity", headers=admin_headers)
    assert res_act.status_code == 200
    assert "activities" in res_act.json()

    # Viewer attempts recent activities -> fails
    res_act_viewer = await client.get("/api/v1/dashboard/recent-activity", headers=viewer_headers)
    assert res_act_viewer.status_code == 403

    # --- TEST GET /dashboard/system-summary ---
    # Admin accesses system summary
    res_sys = await client.get("/api/v1/dashboard/system-summary", headers=admin_headers)
    assert res_sys.status_code == 200
    data_sys = res_sys.json()
    assert "cpu_usage_percent" in data_sys
    assert data_sys["api_status"] == "healthy"

    # Officer attempts system summary -> fails
    res_sys_off = await client.get("/api/v1/dashboard/system-summary", headers=officer_headers)
    assert res_sys_off.status_code == 403

    # --- TEST GET /dashboard/user-summary ---
    # Admin accesses user summary
    res_usr = await client.get("/api/v1/dashboard/user-summary", headers=admin_headers)
    assert res_usr.status_code == 200
    data_usr = res_usr.json()
    assert data_usr["total_users"] > 0
    assert len(data_usr["role_distribution"]) > 0

    # Analyst attempts user summary -> fails
    res_usr_analyst = await client.get("/api/v1/dashboard/user-summary", headers=analyst_headers)
    assert res_usr_analyst.status_code == 403


async def test_dashboard_caching_behavior(client: AsyncClient, db: AsyncSession):
    await create_user_with_role(db, "admin", "Super Admin")
    await db.commit()
    admin_headers = await get_auth_headers(client, "admin")

    await dashboard_cache_service.clear()

    # Initial call - compiles and populates cache
    res1 = await client.get("/api/v1/dashboard/overview", headers=admin_headers)
    assert res1.status_code == 200
    val1 = res1.json()

    # Seed a new detection to database
    det = Detection(
        image_path="/static/uploads/cache_test.jpg",
        filename="cache_test.jpg",
        prediction_label="fire",
        confidence=0.99,
        model_name="CNN_v1",
        model_version="1.0"
    )
    db.add(det)
    await db.commit()

    # Call overview again - should return CACHED value (total_uploaded_images still 3 instead of 4)
    res2 = await client.get("/api/v1/dashboard/overview", headers=admin_headers)
    assert res2.status_code == 200
    val2 = res2.json()
    assert val1["total_uploaded_images"] == val2["total_uploaded_images"]

    # Evict cache explicitly
    await dashboard_cache_service.clear()

    # Call overview third time - should fetch fresh database values (total_uploaded_images is now 4)
    res3 = await client.get("/api/v1/dashboard/overview", headers=admin_headers)
    assert res3.status_code == 200
    val3 = res3.json()
    assert val3["total_uploaded_images"] == val1["total_uploaded_images"] + 1


async def test_monitoring_telemetry_and_health(db: AsyncSession):
    # Verify System telemetry reads correctly
    cpu = system_metrics.get_cpu_usage_percent()
    ram = system_metrics.get_memory_usage()
    disk = system_metrics.get_storage_usage()
    
    assert isinstance(cpu, float)
    assert cpu >= 0.0 and cpu <= 100.0
    assert ram["total_bytes"] > 0
    assert disk["percentage_used"] >= 0.0

    # Verify Health Service active DB check
    db_ok = await health_service.check_database_health(db)
    assert db_ok is True

    storage_ok = health_service.check_storage_health()
    assert storage_ok is True
