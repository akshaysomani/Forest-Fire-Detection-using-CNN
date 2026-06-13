import pytest
import asyncio
import uuid
from datetime import datetime
from unittest.mock import patch
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.role import Role
from app.models.mlops import DeploymentJob, Environment, Release
from app.models.model_registry import RegisteredModel, ModelVersion, ModelArtifact
from app.services.password_service import password_service
from app.services.mlops.config_loader import config_loader
from app.services.mlops.environment_manager import environment_manager
from app.services.mlops.environment_registry import environment_registry
from app.services.mlops.release_registry import release_registry
from app.services.mlops.model_deployment_service import model_deployment_service

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


async def setup_test_users(db: AsyncSession):
    """Creates admin and viewer users and returns their user objects."""
    admin = await create_user_with_role(db, "mlops_admin", "Super Admin")
    viewer = await create_user_with_role(db, "mlops_viewer", "Viewer")
    await db.commit()
    return admin, viewer


async def test_config_loader_vault_decryption():
    """Tests simulated Vault decryption logic (reverse values prefixed with vault::)."""
    raw_config = {
        "database_url": "sqlite+aiosqlite:///app.db",
        "api_key": "vault::123xyz_secret",
        "nested": {
            "token": "vault::abc_token"
        }
    }
    decrypted = config_loader.decrypt_dict_secrets(raw_config)
    assert decrypted["database_url"] == "sqlite+aiosqlite:///app.db"
    assert decrypted["api_key"] == "terces_zyx321"
    assert decrypted["nested"]["token"] == "nekot_cba"


async def test_environment_manager_validation():
    """Tests validation of environment configurations against schemas."""
    # Basic baseline validation (missing keys)
    invalid_config = {"database_url": "sqlite:///app.db"}
    is_valid, err = environment_manager.validate_configuration(invalid_config)
    assert not is_valid
    assert "Missing required configuration properties" in err

    valid_config = {
        "database_url": "sqlite:///app.db",
        "storage_provider": "local",
        "storage_base_dir": "storage_dir"
    }
    is_valid, err = environment_manager.validate_configuration(valid_config)
    assert is_valid
    assert err is None

    # Custom Schema validation
    custom_schema = {"port": "int", "name": "str"}
    is_valid, err = environment_manager.validate_configuration({"port": "8000", "name": "staging"}, custom_schema)
    assert is_valid

    is_valid_fail, err_fail = environment_manager.validate_configuration({"port": "not-an-int", "name": "staging"}, custom_schema)
    assert not is_valid_fail
    assert "expects an integer" in err_fail


async def test_mlops_rbac_endpoints(client: AsyncClient, db: AsyncSession):
    """Verifies that MLOps endpoints enforce correct RBAC permissions."""
    admin, viewer = await setup_test_users(db)
    admin_headers = await get_auth_headers(client, "mlops_admin")
    viewer_headers = await get_auth_headers(client, "mlops_viewer")

    # 1. Trigger deployment - viewer should fail (403)
    dummy_uuid = uuid.uuid4()
    resp = await client.post(
        "/api/v1/deployments",
        headers=viewer_headers,
        json={"environment_id": str(dummy_uuid), "model_version_id": str(dummy_uuid)}
    )
    assert resp.status_code == 403

    # 2. Promote deployment - viewer should fail (403)
    resp = await client.post(
        "/api/v1/deployments/promote",
        headers=viewer_headers,
        json={"deployment_job_id": str(dummy_uuid), "target_environment_id": str(dummy_uuid)}
    )
    assert resp.status_code == 403

    # 3. Rollback deployment - viewer should fail (403)
    resp = await client.post(
        "/api/v1/deployments/rollback",
        headers=viewer_headers,
        json={"environment_id": str(dummy_uuid)}
    )
    assert resp.status_code == 403

    # 4. Read list deployments - viewer should succeed (200)
    resp = await client.get("/api/v1/deployments", headers=viewer_headers)
    assert resp.status_code == 200

    # 5. Read deployment history - viewer should succeed (200)
    resp = await client.get("/api/v1/deployments/history", headers=viewer_headers)
    assert resp.status_code == 200


async def test_full_deployment_workflow(client: AsyncClient, db: AsyncSession):
    """Performs a full deployment, promotion, rollback, and metrics verification."""
    admin, viewer = await setup_test_users(db)
    admin_headers = await get_auth_headers(client, "mlops_admin")

    # 1. Create mock registered model
    model = RegisteredModel(name="test_cnn_model", description="Testing CNN", created_by=admin.id)
    db.add(model)
    await db.commit()

    # 2. Create mock model version (status must be Approved for lifecycle check)
    model_version = ModelVersion(
        model_id=model.id,
        version="1.0.0",
        status="Approved",
        created_by=admin.id,
        metrics={"val_accuracy": 0.95, "val_loss": 0.05},
        hyperparameters={"lr": 0.001}
    )
    db.add(model_version)
    await db.commit()

    # 3. Create mock weights artifact (required by deploy_version lifecycle)
    artifact = ModelArtifact(
        model_version_id=model_version.id,
        name="best_weights",
        artifact_type="weights",
        uri="s3://mock-bucket/models/best_weights.pth",
        created_by=admin.id
    )
    db.add(artifact)
    await db.commit()

    # 4. Create staging and production environments
    staging_env = await environment_registry.create_environment(
        db=db,
        name="staging",
        description="Staging Environment",
        config_data={
            "database_url": "sqlite:///staging.db",
            "storage_provider": "local",
            "storage_base_dir": "/staging/storage"
        }
    )
    prod_env = await environment_registry.create_environment(
        db=db,
        name="production",
        description="Production Environment",
        config_data={
            "database_url": "sqlite:///production.db",
            "storage_provider": "local",
            "storage_base_dir": "/production/storage"
        }
    )

    # Trigger deployment to staging via REST API
    # Since deployment tracking will update lifecycle to "Staging" state, we patch the load_and_set_active_model just in case.
    with patch("app.services.inference.model_manager.model_manager.load_and_set_active_model") as mock_load:
        resp = await client.post(
            "/api/v1/deployments",
            headers=admin_headers,
            json={
                "environment_id": str(staging_env.id),
                "model_version_id": str(model_version.id)
            }
        )
        assert resp.status_code == 201
        job_data = resp.json()
        assert job_data["status"] == "succeeded"
        assert len(job_data["steps"]) == 4
        assert job_data["steps"][0]["status"] == "completed"

        # Verification of DB updates:
        # A release should be created for this environment deployment.
        db_staging = await environment_registry.get_environment(db, staging_env.id)
        assert db_staging.current_release_id is not None

        # Verify model version lifecycle transitioned to 'Staging'
        await db.refresh(model_version)
        assert model_version.status == "Staging"

        # 5. Rollback verification.
        # Currently, staging only has 1 successful deployment. A rollback attempt should return validation error.
        resp_rb_fail = await client.post(
            "/api/v1/deployments/rollback",
            headers=admin_headers,
            json={"environment_id": str(staging_env.id)}
        )
        assert resp_rb_fail.status_code == 422
        assert "No previous stable deployment found" in resp_rb_fail.json()["error"]["message"]

        # Deploy a second model version to staging to enable rollback
        await asyncio.sleep(1.1)
        model_version_2 = ModelVersion(
            model_id=model.id,
            version="1.0.1",
            status="Approved",
            created_by=admin.id,
            metrics={"val_accuracy": 0.96},
            hyperparameters={"lr": 0.002}
        )
        db.add(model_version_2)
        await db.commit()

        artifact_2 = ModelArtifact(
            model_version_id=model_version_2.id,
            name="best_weights_2",
            artifact_type="weights",
            uri="s3://mock-bucket/models/best_weights_2.pth",
            created_by=admin.id
        )
        db.add(artifact_2)
        await db.commit()

        # Deploy 1.0.1 to staging
        resp_deploy_2 = await client.post(
            "/api/v1/deployments",
            headers=admin_headers,
            json={
                "environment_id": str(staging_env.id),
                "model_version_id": str(model_version_2.id)
            }
        )
        assert resp_deploy_2.status_code == 201

        # Now rollback staging (should revert to version 1.0.0)
        resp_rb = await client.post(
            "/api/v1/deployments/rollback",
            headers=admin_headers,
            json={"environment_id": str(staging_env.id)}
        )
        assert resp_rb.status_code == 200
        rb_data = resp_rb.json()
        assert rb_data["status"] == "succeeded"
        assert rb_data["model_version_id"] == str(model_version.id)  # reverted back to 1.0.0

        # 6. Promote staging deployment to production
        # Promotion status needs model status eligible. Since 1.0.0 is still in Staging status, we can promote it.
        resp_promo = await client.post(
            "/api/v1/deployments/promote",
            headers=admin_headers,
            json={
                "deployment_job_id": rb_data["id"],
                "target_environment_id": str(prod_env.id)
            }
        )
        assert resp_promo.status_code == 200
        promo_data = resp_promo.json()
        assert promo_data["status"] == "succeeded"

        # Model manager should be triggered for production hot-swap
        mock_load.assert_called_once()
        await db.refresh(model_version)
        assert model_version.status == "Production"

        # 7. Verify list deployments and history API endpoints
        resp_list = await client.get("/api/v1/deployments", headers=admin_headers)
        assert resp_list.status_code == 200
        assert len(resp_list.json()) >= 1

        resp_hist = await client.get("/api/v1/deployments/history", headers=admin_headers)
        assert resp_hist.status_code == 200
        assert len(resp_hist.json()) >= 4  # Staging (1.0.0), Staging (1.0.1), Rollback (1.0.0), Production (1.0.0)

        resp_envs = await client.get("/api/v1/deployments/environments", headers=admin_headers)
        assert resp_envs.status_code == 200
        assert len(resp_envs.json()) == 2

        resp_rels = await client.get("/api/v1/deployments/releases", headers=admin_headers)
        assert resp_rels.status_code == 200
        assert len(resp_rels.json()) == 4

        # Check observability/metrics API
        resp_metrics = await client.get("/api/v1/deployments/observability/metrics", headers=admin_headers)
        assert resp_metrics.status_code == 200
        m_summary = resp_metrics.json()
        assert m_summary["total_deployments"] >= 4
        assert m_summary["rollback_frequency"] > 0.0
        assert m_summary["deployment_success_rate"] == 1.0
