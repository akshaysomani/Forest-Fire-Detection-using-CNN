import pytest
import uuid
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from app.models.user import User
from app.models.role import Role
from app.models.dataset import Dataset, DatasetCategory
from app.models.training import TrainingRun, TrainingCheckpoint
from app.models.model_registry import (
    RegisteredModel,
    ModelVersion,
    ModelArtifact,
    ModelMetadata,
    ModelDeployment,
    ModelApproval,
    ModelLifecycleEvent,
    ModelAuditLog
)
from app.services.password_service import password_service
from app.services.model_registry.model_version_service import model_version_service
from app.services.model_registry.model_governance_engine import model_governance_engine
from app.services.model_registry.artifact_storage_service import artifact_storage_service
from app.services.inference.model_manager import model_manager

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


async def setup_test_environment(db: AsyncSession):
    """Creates admin and viewer users and returns their user objects."""
    admin = await create_user_with_role(db, "admin_user", "Super Admin")
    viewer = await create_user_with_role(db, "viewer_user", "Viewer")
    await db.commit()
    return admin, viewer


async def test_model_family_registration_and_rbac(client: AsyncClient, db: AsyncSession):
    admin, viewer = await setup_test_environment(db)
    admin_headers = await get_auth_headers(client, "admin_user")
    viewer_headers = await get_auth_headers(client, "viewer_user")

    # 1. Test creation by viewer (Should fail with 403)
    viewer_res = await client.post(
        "/api/v1/models",
        headers=viewer_headers,
        json={"name": "custom_cnn", "description": "Baseline Custom CNN"}
    )
    assert viewer_res.status_code == 403

    # 2. Test creation by admin (Should succeed with 201)
    admin_res = await client.post(
        "/api/v1/models",
        headers=admin_headers,
        json={"name": "custom_cnn", "description": "Baseline Custom CNN"}
    )
    assert admin_res.status_code == 201
    model_data = admin_res.json()
    assert model_data["name"] == "custom_cnn"
    assert model_data["description"] == "Baseline Custom CNN"
    assert "id" in model_data

    # 3. Test list models
    list_res = await client.get("/api/v1/models", headers=viewer_headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(m["name"] == "custom_cnn" for m in list_data["items"])


async def test_version_registration_semver_and_auto_artifacts(client: AsyncClient, db: AsyncSession):
    admin, viewer = await setup_test_environment(db)
    admin_headers = await get_auth_headers(client, "admin_user")
    viewer_headers = await get_auth_headers(client, "viewer_user")

    # 1. Create model family definition
    m_res = await client.post(
        "/api/v1/models",
        headers=admin_headers,
        json={"name": "resnet18", "description": "ResNet18 Model family"}
    )
    assert m_res.status_code == 201
    model_id = m_res.json()["id"]

    # 2. Seed a mock training run and checkpoint
    category = DatasetCategory(name="Smoke Tests", description="Category for testing")
    db.add(category)
    await db.commit()

    ds = Dataset(name="Test DS", category_id=category.id, user_id=admin.id, status="active")
    db.add(ds)
    await db.commit()

    run = TrainingRun(
        dataset_id=ds.id,
        status="completed",
        model_name="resnet18",
        hyperparameters={"learning_rate": 0.001, "batch_size": 32},
        user_id=admin.id,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    db.add(run)
    await db.commit()

    checkpoint = TrainingCheckpoint(
        run_id=run.id,
        epoch=10,
        val_loss=0.15,
        val_accuracy=0.92,
        checkpoint_path="runs/test_run/checkpoints/best_model.pth",
        is_best=True
    )
    db.add(checkpoint)
    await db.commit()

    # Mock artifact_storage_service.verify_exists & get_file_metadata
    with patch("app.services.model_registry.artifact_storage_service.artifact_storage_service.verify_exists", return_value=True), \
         patch("app.services.model_registry.artifact_storage_service.artifact_storage_service.get_file_metadata", return_value=(1024, "mock_sha256_checksum")):
        
        # Register first version (Should resolve to 1.0.0 since no versions exist)
        v_res1 = await client.post(
            "/api/v1/models/versions",
            headers=admin_headers,
            json={
                "model_id": model_id,
                "training_run_id": str(run.id),
                "checkpoint_id": str(checkpoint.id),
                "description": "First version release notes"
            }
        )
        assert v_res1.status_code == 201
        v1_data = v_res1.json()
        assert v1_data["version"] == "1.0.0"
        assert v1_data["status"] == "Draft"
        assert v1_data["metrics"]["val_accuracy"] == 0.92
        v1_id = v1_data["id"]

        # Register second version with "patch" increment (Should resolve to 1.0.1)
        v_res2 = await client.post(
            "/api/v1/models/versions",
            headers=admin_headers,
            json={
                "model_id": model_id,
                "training_run_id": str(run.id),
                "checkpoint_id": str(checkpoint.id),
                "description": "Patch update notes"
            }
        )
        assert v_res2.status_code == 201
        v2_data = v_res2.json()
        assert v2_data["version"] == "1.0.1"

        # Verify artifacts were registered automatically (Weights weights checkpoint)
        art_res = await client.get(f"/api/v1/models/artifacts?model_version_id={v1_id}", headers=viewer_headers)
        assert art_res.status_code == 200
        artifacts = art_res.json()
        assert len(artifacts) >= 1
        assert any(a["artifact_type"] == "weights" for a in artifacts)
        assert artifacts[0]["checksum"] == "mock_sha256_checksum"


async def test_governance_validation_and_approvals(client: AsyncClient, db: AsyncSession):
    admin, viewer = await setup_test_environment(db)
    admin_headers = await get_auth_headers(client, "admin_user")
    viewer_headers = await get_auth_headers(client, "viewer_user")

    # 1. Create model family and low-accuracy model version
    m_res = await client.post(
        "/api/v1/models",
        headers=admin_headers,
        json={"name": "mobilenet_v3", "description": "MobileNetV3"}
    )
    model_id = m_res.json()["id"]

    category = DatasetCategory(name="Smoke Tests", description="Category for testing")
    db.add(category)
    await db.commit()
    ds = Dataset(name="Test DS", category_id=category.id, user_id=admin.id, status="active")
    db.add(ds)
    await db.commit()

    run = TrainingRun(
        dataset_id=ds.id,
        status="completed",
        model_name="mobilenet_v3",
        hyperparameters={},
        user_id=admin.id
    )
    db.add(run)
    await db.commit()

    # Bad checkpoint: low accuracy (72% < 80%)
    checkpoint_bad = TrainingCheckpoint(
        run_id=run.id,
        epoch=5,
        val_loss=0.65,
        val_accuracy=0.72,
        checkpoint_path="runs/bad_run/best.pth",
        is_best=True
    )
    db.add(checkpoint_bad)
    await db.commit()

    # Mock artifact check
    with patch("app.services.model_registry.artifact_storage_service.artifact_storage_service.verify_exists", return_value=True), \
         patch("app.services.model_registry.artifact_storage_service.artifact_storage_service.get_file_metadata", return_value=(512, "sha256")):
        
        # Register version
        v_res = await client.post(
            "/api/v1/models/versions",
            headers=admin_headers,
            json={"model_id": model_id, "training_run_id": str(run.id), "checkpoint_id": str(checkpoint_bad.id)}
        )
        assert v_res.status_code == 201
        v_id = v_res.json()["id"]

        # 2. Try requesting approval (Should fail accuracy threshold rule gate with 422)
        app_res1 = await client.post(
            "/api/v1/models/approve/request",
            headers=admin_headers,
            json={"model_version_id": v_id, "target_stage": "Approved", "request_notes": "Deploying mobilenet"}
        )
        assert app_res1.status_code == 422
        assert "accuracy" in app_res1.json()["error"]["message"].lower()

        # Update metrics to bypass gate in test DB session
        version_db = await db.get(ModelVersion, uuid.UUID(v_id))
        version_db.metrics = {"val_accuracy": 0.86, "val_loss": 0.12, "accuracy": 0.86}
        await db.commit()

        # Try requesting approval again (Should succeed with 201)
        app_res2 = await client.post(
            "/api/v1/models/approve/request",
            headers=admin_headers,
            json={"model_version_id": v_id, "target_stage": "Approved", "request_notes": "Valid Mobilenet"}
        )
        assert app_res2.status_code == 201
        approval_id = app_res2.json()["id"]
        assert app_res2.json()["status"] == "pending"

        # Check version transitioned to "Validation" status
        v_check = await client.get(f"/api/v1/models/versions/{v_id}", headers=viewer_headers)
        assert v_check.json()["status"] == "Validation"

        # 3. Submit review approval
        rev_res = await client.post(
            "/api/v1/models/approve",
            headers=admin_headers,
            json={"approval_id": approval_id, "status": "approved", "review_notes": "Passes safety check."}
        )
        assert rev_res.status_code == 200
        assert rev_res.json()["status"] == "approved"

        # Check version status is now "Approved"
        v_check2 = await client.get(f"/api/v1/models/versions/{v_id}", headers=viewer_headers)
        assert v_check2.json()["status"] == "Approved"


async def test_deployment_hot_swapping_and_rollback(client: AsyncClient, db: AsyncSession):
    admin, viewer = await setup_test_environment(db)
    admin_headers = await get_auth_headers(client, "admin_user")
    viewer_headers = await get_auth_headers(client, "viewer_user")

    # 1. Register model family and two approved model versions
    m_res = await client.post(
        "/api/v1/models",
        headers=admin_headers,
        json={"name": "efficientnet_b0", "description": "EfficientNet"}
    )
    model_id = m_res.json()["id"]

    # Version 1 (v1.0.0)
    version1 = ModelVersion(
        model_id=uuid.UUID(model_id),
        version="1.0.0",
        status="Approved",
        metrics={"accuracy": 0.85},
        hyperparameters={}
    )
    # Version 2 (v1.0.1)
    version2 = ModelVersion(
        model_id=uuid.UUID(model_id),
        version="1.0.1",
        status="Approved",
        metrics={"accuracy": 0.89},
        hyperparameters={}
    )
    db.add_all([version1, version2])
    await db.commit()
    await db.refresh(version1)
    await db.refresh(version2)

    # Register weights artifacts
    art1 = ModelArtifact(model_version_id=version1.id, name="best1.pth", artifact_type="weights", uri="runs/r1/best.pth")
    art2 = ModelArtifact(model_version_id=version2.id, name="best2.pth", artifact_type="weights", uri="runs/r2/best.pth")
    db.add_all([art1, art2])
    await db.commit()

    # Mock model loader to bypass PyTorch load in model_manager hot-swapping
    with patch("app.services.inference.model_loader.model_loader.load_model_from_checkpoint", return_value=None):
        # 2. Deploy version 1 to production
        dep_res1 = await client.post(
            "/api/v1/models/deploy",
            headers=admin_headers,
            json={"model_version_id": str(version1.id), "environment": "production"}
        )
        assert dep_res1.status_code == 200
        assert dep_res1.json()["environment"] == "production"
        assert dep_res1.json()["status"] == "active"

        # Check active loaded model in ModelManager matches version1
        details1 = model_manager.get_active_model_details()
        assert details1["run_id"] == str(version1.id)
        assert details1["checkpoint_path"] == "runs/r1/best.pth"

        # Deploy version 2 to production (Should replace version 1)
        dep_res2 = await client.post(
            "/api/v1/models/deploy",
            headers=admin_headers,
            json={"model_version_id": str(version2.id), "environment": "production"}
        )
        assert dep_res2.status_code == 200

        # Check pointer updated in ModelManager
        details2 = model_manager.get_active_model_details()
        assert details2["run_id"] == str(version2.id)
        assert details2["checkpoint_path"] == "runs/r2/best.pth"

        # 3. Rollback deployment (Should restore version 1)
        rollback_res = await client.post(
            "/api/v1/models/rollback",
            headers=admin_headers,
            json={"model_id": model_id, "environment": "production"}
        )
        assert rollback_res.status_code == 200
        assert rollback_res.json()["model_version_id"] == str(version1.id)

        # Check pointer reverted in ModelManager
        details3 = model_manager.get_active_model_details()
        assert details3["run_id"] == str(version1.id)
        assert details3["checkpoint_path"] == "runs/r1/best.pth"


async def test_comparison_history_and_observability(client: AsyncClient, db: AsyncSession):
    admin, viewer = await setup_test_environment(db)
    admin_headers = await get_auth_headers(client, "admin_user")
    viewer_headers = await get_auth_headers(client, "viewer_user")

    # 1. Register family and two versions
    model = RegisteredModel(name="test_obs", description="observability checks")
    db.add(model)
    await db.commit()

    v1 = ModelVersion(model_id=model.id, version="1.0.0", status="Approved", metrics={"accuracy": 0.81}, hyperparameters={"learning_rate": 0.001})
    v2 = ModelVersion(model_id=model.id, version="1.1.0", status="Approved", metrics={"accuracy": 0.87}, hyperparameters={"learning_rate": 0.002})
    db.add_all([v1, v2])
    await db.commit()

    # Compare versions API
    comp_res = await client.get(
        f"/api/v1/models/versions?version_a={v1.id}&version_b={v2.id}",
        headers=viewer_headers
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert "metrics_diff" in comp_data
    assert abs(comp_data["metrics_diff"]["accuracy"]["difference"] - 0.06) < 1e-6
    assert comp_data["hyperparameters_diff"]["learning_rate"]["changed"] is True

    # Retrieve history API (logs transition history)
    hist_res = await client.get(f"/api/v1/models/history?model_version_id={v1.id}", headers=viewer_headers)
    assert hist_res.status_code == 200

    # Retrieve metrics API (observability)
    metrics_res = await client.get("/api/v1/models/observability/metrics", headers=viewer_headers)
    assert metrics_res.status_code == 200
    metrics_data = metrics_res.json()
    assert "total_model_families" in metrics_data
    assert "total_model_versions" in metrics_data
