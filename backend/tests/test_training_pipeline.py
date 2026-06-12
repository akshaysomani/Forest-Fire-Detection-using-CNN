import io
import pytest
import uuid
import threading
import torch
import torch.nn as nn
from PIL import Image
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from app.models.user import User
from app.models.role import Role
from app.models.dataset import Dataset, DatasetCategory, DatasetLabel, DatasetFile
from app.models.training import TrainingRun, TrainingCheckpoint
from app.services.training.training_config import HyperparametersConfig
from app.services.training.model_factory import model_factory
from app.services.training.dataset_splitter import dataset_splitter
from app.services.training.dataset_validator import dataset_validator
from app.services.training.data_statistics import data_statistics
from app.services.training.run_manager import run_manager
from app.services.storage_service import storage_service


pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def seed_dataset_data(db: AsyncSession):
    from app.services.dataset_service import dataset_service
    await dataset_service.seed_categories_and_labels(db)
    await db.commit()


def create_dummy_image_bytes(size=(224, 224), color="red") -> bytes:
    """Helper to generate valid PNG bytes for validator checks."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def get_auth_headers(client: AsyncClient, role_name: str, db: AsyncSession) -> dict:
    """Helper to register and login a user with a specific seeded role."""
    username = f"user_{role_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}"
    email = f"{username}@forestfire.org"
    password = "SuperPassword123!"

    # 1. Register user
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password,
            "confirm_password": password
        }
    )
    assert reg_res.status_code == 201

    # 2. Query and assign role in DB
    query = select(Role).where(Role.name == role_name)
    res = await db.execute(query)
    role_obj = res.scalar_one()

    query_user = select(User).where(User.username == username).options(selectinload(User.roles))
    res_user = await db.execute(query_user)
    user_obj = res_user.scalar_one()
    if role_obj not in user_obj.roles:
        user_obj.roles.append(role_obj)
    await db.commit()

    # 3. Login user
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ==========================================
# 1. CONFIGURATION & SCHEMA VALIDATIONS
# ==========================================

async def test_hyperparameters_validation():
    # Valid hyperparameter instantiation
    hp = HyperparametersConfig(learning_rate=0.001, batch_size=32, epochs=5)
    assert hp.learning_rate == 0.001
    assert hp.batch_size == 32
    assert hp.epochs == 5

    # Invalid learning rate (raises error)
    with pytest.raises(ValueError):
        HyperparametersConfig(learning_rate=-0.01)

    # Invalid learning rate too high
    with pytest.raises(ValueError):
        HyperparametersConfig(learning_rate=0.5)

    # Invalid batch_size (not power of 2)
    with pytest.raises(ValueError):
        HyperparametersConfig(batch_size=15)

    # Invalid optimizer choice
    with pytest.raises(ValueError):
        HyperparametersConfig(optimizer="adagrad")


# ==========================================
# 2. MODEL FACTORY CHECKS
# ==========================================

async def test_model_factory_generation():
    # Test Custom CNN
    model = model_factory.create_model("custom_cnn", num_classes=2, pretrained=False)
    assert isinstance(model, nn.Module)
    x = torch.randn(2, 3, 224, 224)
    out = model(x)
    assert out.shape == (2, 2)

    # Test ResNet-18
    model_r18 = model_factory.create_model("resnet18", num_classes=2, pretrained=False)
    assert isinstance(model_r18, nn.Module)
    out_r18 = model_r18(x)
    assert out_r18.shape == (2, 2)

    # Test MobileNetV3
    model_m = model_factory.create_model("mobilenet_v3", num_classes=2, pretrained=False)
    assert isinstance(model_m, nn.Module)
    out_m = model_m(x)
    assert out_m.shape == (2, 2)

    # Test EfficientNet-B0
    model_e = model_factory.create_model("efficientnet_b0", num_classes=2, pretrained=False)
    assert isinstance(model_e, nn.Module)
    out_e = model_e(x)
    assert out_e.shape == (2, 2)

    # Test Unsupported
    with pytest.raises(ValueError):
        model_factory.create_model("alexnet")


# ==========================================
# 3. STRATIFIED SPLITTER TESTS
# ==========================================

async def test_dataset_splitter():
    label_a = uuid.uuid4()
    label_b = uuid.uuid4()

    # Create mock dataset file list
    files = []
    # 8 files of label A, 12 files of label B (20 files total)
    for i in range(20):
        label_id = label_a if i < 8 else label_b
        files.append(DatasetFile(
            dataset_id=uuid.uuid4(),
            file_path=f"path_{i}.jpg",
            filename=f"file_{i}.jpg",
            file_size=1000,
            md5_hash=f"hash_{i}",
            label_id=label_id
        ))

    train, val, test = dataset_splitter.split_dataset(files, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1, seed=42)

    # Sum counts must equal total
    assert len(train) + len(val) + len(test) == 20

    # Assert ratios (approximate due to small dataset size ceiling checks)
    assert len(train) >= 12
    assert len(val) >= 2
    assert len(test) >= 2


# ==========================================
# 4. PRE-TRAINING INTEGRITY VALIDATOR
# ==========================================

async def test_dataset_validator_rules(db: AsyncSession):
    # Empty files (raises error)
    is_ok, err = await dataset_validator.validate_dataset_files([], min_files=10)
    assert not is_ok
    assert "insufficient images" in err.lower()

    # Seed some dataset files
    label_ids = sorted(list({l.id for l in (await db.execute(select(DatasetLabel))).scalars().all()}))
    assert len(label_ids) >= 2

    files_unlabeled = [
        DatasetFile(
            dataset_id=uuid.uuid4(), file_path="p.jpg", filename="p.jpg", file_size=100, md5_hash=f"h{i}"
        ) for i in range(10)
    ]
    # Unlabeled files (raises error)
    is_ok, err = await dataset_validator.validate_dataset_files(files_unlabeled)
    assert not is_ok
    assert "unlabeled" in err.lower()

    # Single label diversity files (raises error)
    files_single_label = [
        DatasetFile(
            dataset_id=uuid.uuid4(), file_path=f"p{i}.jpg", filename=f"p{i}.jpg", file_size=100, md5_hash=f"h{i}", label_id=label_ids[0]
        ) for i in range(12)
    ]
    is_ok, err = await dataset_validator.validate_dataset_files(files_single_label)
    assert not is_ok
    assert "class diversity" in err.lower()


# ==========================================
# 5. DATASET STATISTICS CHECKS
# ==========================================

async def test_data_statistics(db: AsyncSession):
    # Find dataset labels
    lbl_res = await db.execute(select(DatasetLabel).limit(2))
    labels = lbl_res.scalars().all()
    assert len(labels) >= 2

    files = [
        DatasetFile(
            dataset_id=uuid.uuid4(),
            file_path=f"runs/p{i}.jpg",
            filename=f"p{i}.jpg",
            file_size=1000,
            md5_hash=f"hash{i}",
            label_id=labels[0].id if i < 6 else labels[1].id,
            label=labels[0] if i < 6 else labels[1],
            metadata_json={"width": 400, "height": 300}
        ) for i in range(10)
    ]

    # Mock storage read_file
    dummy_img = create_dummy_image_bytes(size=(200, 200))
    with patch.object(storage_service, "read_file", return_value=dummy_img):
        stats = await data_statistics.compute_statistics(files)
        assert stats["total_files"] == 10
        assert stats["avg_width"] == 400.0
        assert stats["avg_height"] == 300.0
        assert len(stats["channel_mean"]) == 3
        assert len(stats["channel_std"]) == 3


# ==========================================
# 6. API CONTROLLER TESTS
# ==========================================

async def test_training_apis(client: AsyncClient, db: AsyncSession):
    admin_headers = await get_auth_headers(client, "Super Admin", db)
    viewer_headers = await get_auth_headers(client, "Viewer", db)

    # 1. Setup mock Category and Dataset in DB
    cat_res = await db.execute(select(DatasetCategory).limit(1))
    cat = cat_res.scalar_one()

    # Create dummy user
    query_user = select(User).limit(1)
    res_user = await db.execute(query_user)
    user_obj = res_user.scalar_one()

    ds = Dataset(name=f"Training DS {uuid.uuid4().hex[:6]}", category_id=cat.id, user_id=user_obj.id, status="active")
    db.add(ds)
    await db.commit()

    # Check RBAC access controls - Viewer starts training (Should fail with 403)
    start_fail = await client.post(
        "/api/v1/training/start",
        headers=viewer_headers,
        json={
            "dataset_id": str(ds.id),
            "model_name": "custom_cnn",
            "hyperparameters": {"epochs": 2}
        }
    )
    assert start_fail.status_code == 403

    # Start training with invalid model parameter (Should fail with 422)
    start_bad_model = await client.post(
        "/api/v1/training/start",
        headers=admin_headers,
        json={
            "dataset_id": str(ds.id),
            "model_name": "vgg16",
            "hyperparameters": {"epochs": 2}
        }
    )
    assert start_bad_model.status_code == 422

    # Start training with invalid hyperparameters (Should fail with 422)
    start_bad_hparams = await client.post(
        "/api/v1/training/start",
        headers=admin_headers,
        json={
            "dataset_id": str(ds.id),
            "model_name": "custom_cnn",
            "hyperparameters": {"batch_size": 15}
        }
    )
    assert start_bad_hparams.status_code == 422

    # Mock background thread start execution to prevent running training loop in tests
    with patch("app.services.training.training_engine.TrainingEngine.start_training_run", return_value=uuid.uuid4()):
        # Start training successfully as Admin
        start_res = await client.post(
            "/api/v1/training/start",
            headers=admin_headers,
            json={
                "dataset_id": str(ds.id),
                "model_name": "custom_cnn",
                "hyperparameters": {"epochs": 2, "batch_size": 32}
            }
        )
        assert start_res.status_code == 202
        run_data = start_res.json()
        assert run_data["status"] == "pending"
        run_id = run_data["id"]

        # Register running mock in run manager
        dummy_event = threading.Event()
        dummy_thread = threading.Thread()
        run_manager.register_run(str(run_id), dummy_thread, dummy_event)

        # Query active status (Should succeed with 200)
        status_res = await client.get(f"/api/v1/training/status/{run_id}", headers=viewer_headers)
        assert status_res.status_code == 200
        assert status_res.json()["model_name"] == "custom_cnn"

        # List runs (Should succeed with 200)
        list_res = await client.get("/api/v1/training/runs", headers=viewer_headers)
        assert list_res.status_code == 200
        assert list_res.json()["total"] >= 1

        # Retrieve checkpoints list (empty initially)
        check_res = await client.get(f"/api/v1/training/checkpoints/{run_id}", headers=viewer_headers)
        assert check_res.status_code == 200
        assert len(check_res.json()) == 0

        # Retrieve metrics list (empty initially)
        metric_res = await client.get(f"/api/v1/training/metrics/{run_id}", headers=viewer_headers)
        assert metric_res.status_code == 200
        assert len(metric_res.json()) == 0

        # Stop active training run gracefully
        stop_res = await client.post(f"/api/v1/training/stop/{run_id}", headers=admin_headers)
        assert stop_res.status_code == 200
        assert "graceful stop" in stop_res.json()["message"].lower()

        # Clean up mock run registry
        run_manager.deregister_run(str(run_id))
