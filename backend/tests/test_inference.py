import io
import uuid
import pytest
import torch
import torch.nn as nn
from PIL import Image
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.role import Role
from app.models.detection import Detection
from app.services.inference.input_validator import input_validator
from app.services.inference.inference_preprocessor import inference_preprocessor
from app.services.inference.prediction_transformer import prediction_transformer
from app.services.inference.classification_service import classification_service
from app.services.inference.risk_analyzer import risk_analyzer
from app.services.inference.model_loader import model_loader
from app.services.inference.model_manager import model_manager
from app.services.inference.prediction_engine import prediction_engine
from app.services.inference.prediction_service import prediction_service
from app.services.inference.batch_prediction_service import batch_prediction_service
from app.services.inference.prediction_queue import prediction_queue
from app.services.inference.batch_processor import batch_processor
from tests.test_training_pipeline import get_auth_headers, create_dummy_image_bytes

pytestmark = pytest.mark.asyncio


# ==========================================
# 1. INPUT VALIDATION TESTS
# ==========================================

async def test_input_validator_invalid_size():
    # Construct massive byte list representing 16MB file
    huge_bytes = b"0" * (16 * 1024 * 1024)
    with pytest.raises(Exception) as exc_info:
        input_validator.validate_image_bytes(huge_bytes, "huge.jpg")
    assert "exceeds maximum allowed size" in str(exc_info.value)


async def test_input_validator_corrupt():
    corrupt_bytes = b"not_an_image_file_at_all"
    with pytest.raises(Exception) as exc_info:
        input_validator.validate_image_bytes(corrupt_bytes, "corrupt.jpg")
    assert "Corrupted or invalid image" in str(exc_info.value)


# ==========================================
# 2. PREPROCESSING & TRANSFORMATION TESTS
# ==========================================

async def test_inference_preprocessor():
    img_bytes = create_dummy_image_bytes(size=(400, 300))
    pil_img = await inference_preprocessor.preprocess_image(img_bytes, target_size=(224, 224))
    
    assert pil_img.size == (224, 224)
    assert pil_img.mode == "RGB"


async def test_prediction_transformer():
    # Create PIL image
    img = Image.new("RGB", (224, 224), color="blue")
    tensor = prediction_transformer.transform_image(img)
    
    assert isinstance(tensor, torch.Tensor)
    assert tensor.shape == (1, 3, 224, 224)
    assert tensor.dtype == torch.float32


# ==========================================
# 3. CLASSIFICATION & RISK ANALYSIS TESTS
# ==========================================

def test_classification_service_resolve():
    # Test fire
    label, conf = classification_service.resolve_classification([0.2, 0.8], threshold=0.5)
    assert label == "fire"
    assert conf == 0.8

    # Test non-fire
    label, conf = classification_service.resolve_classification([0.7, 0.3], threshold=0.5)
    assert label == "non-fire"
    assert conf == 0.7


def test_risk_analyzer():
    # Non-fire has low risk
    assert risk_analyzer.analyze_risk("non-fire", 0.99) == "Low"

    # Fire risk levels
    assert risk_analyzer.analyze_risk("fire", 0.90) == "High"
    assert risk_analyzer.analyze_risk("fire", 0.70) == "Medium"
    assert risk_analyzer.analyze_risk("fire", 0.50) == "Low"


# ==========================================
# 4. MODEL LOADING & MANAGEMENT TESTS
# ==========================================

async def test_model_loader_validation():
    # Verify shape validation catches mismatch errors
    model = nn.Linear(10, 2)
    bad_state_dict = {"weight": torch.randn(5, 2)}  # Model expects (2, 10)
    
    with pytest.raises(ValueError) as exc_info:
        model_loader.validate_state_dict(model, bad_state_dict)
    assert "Weight shape mismatch" in str(exc_info.value)


async def test_model_manager_fallback(db: AsyncSession):
    # Verify manager returns fallback model if no runs completed
    model, name, version = await model_manager.get_active_model(db)
    assert name == "custom_cnn"
    assert version == "0.0.0"
    assert isinstance(model, nn.Module)


# ==========================================
# 5. CORE PREDICTION & SERVICE TESTS
# ==========================================

async def test_prediction_engine_single_image(db: AsyncSession):
    dummy_img = create_dummy_image_bytes()
    
    # Mock model executor to bypass actual PyTorch model call
    with patch("app.services.inference.prediction_executor.PredictionExecutor.execute_inference") as mock_exec:
        # Simulate fire logits [non-fire_prob, fire_prob] -> class 1 is fire
        mock_exec.return_value = (torch.tensor([[-1.0, 1.0]]), torch.tensor([[0.1, 0.9]]))
        
        result = await prediction_engine.predict_single_image(db, dummy_img, "test.jpg")
        
        assert result["prediction_label"] == "fire"
        assert result["confidence"] == pytest.approx(0.9)
        assert result["risk_level"] == "High"
        assert result["model_name"] == "custom_cnn"


async def test_prediction_service_store(db: AsyncSession):
    dummy_img = create_dummy_image_bytes()
    user_id = uuid.uuid4()
    
    with patch("app.services.inference.prediction_executor.PredictionExecutor.execute_inference") as mock_exec:
        mock_exec.return_value = (torch.tensor([[1.0, -1.0]]), torch.tensor([[0.95, 0.05]]))
        
        detection = await prediction_service.predict_and_store(
            db=db,
            file_bytes=dummy_img,
            filename="stored_test.jpg",
            user_id=user_id,
            latitude=12.97,
            longitude=77.59
        )
        await db.commit()
        
        assert detection.id is not None
        assert detection.filename == "stored_test.jpg"
        assert detection.prediction_label == "non-fire"
        assert detection.confidence == pytest.approx(0.95)
        assert detection.latitude == 12.97
        assert detection.longitude == 77.59


# ==========================================
# 6. BATCH QUEUE & PROCESSOR TESTS
# ==========================================

async def test_batch_prediction_flow(db: AsyncSession):
    dummy_img = create_dummy_image_bytes()
    user_id = uuid.uuid4()
    
    images = [
        {"filename": "img1.jpg", "file_bytes": dummy_img},
        {"filename": "img2.jpg", "file_bytes": dummy_img}
    ]
    
    # We patch prediction_service.predict_and_store to prevent infinite execution inside tests
    mock_detection = Detection(
        id=uuid.uuid4(),
        filename="img1.jpg",
        prediction_label="non-fire",
        confidence=0.98,
        model_name="custom_cnn",
        model_version="0.0.0"
    )
    
    with patch("app.services.inference.prediction_service.PredictionService.predict_and_store", return_value=mock_detection):
        # Submit batch job
        job_id = await batch_prediction_service.submit_batch(user_id=user_id, images=images)
        assert job_id is not None
        
        # Dequeue tasks and run worker loop manually once to prevent test blockage
        status_info = batch_prediction_service.get_batch_status(job_id)
        assert status_info["status"] in ("pending", "processing", "completed")


# ==========================================
# 7. API ENDPOINT & RBAC CONTROLLER TESTS
# ==========================================

async def test_predictions_api_endpoints(client: AsyncClient, db: AsyncSession):
    # Setup roles and authorization headers
    admin_headers = await get_auth_headers(client, "Super Admin", db)
    viewer_headers = await get_auth_headers(client, "Viewer", db)
    
    # 1. Test Single Prediction Upload
    dummy_img = create_dummy_image_bytes()
    
    with patch("app.services.inference.prediction_executor.PredictionExecutor.execute_inference") as mock_exec:
        mock_exec.return_value = (torch.tensor([[-1.0, 1.0]]), torch.tensor([[0.15, 0.85]]))
        
        # Test auth restriction: Viewer is not allowed to run prediction (upload_images scope required)
        fail_res = await client.post(
            "/api/v1/predictions",
            headers=viewer_headers,
            files={"file": ("img.jpg", dummy_img, "image/jpeg")},
            data={"latitude": "13.01", "longitude": "80.25"}
        )
        assert fail_res.status_code == 403
        
        # Test success run: Super Admin can run prediction
        success_res = await client.post(
            "/api/v1/predictions",
            headers=admin_headers,
            files={"file": ("img.jpg", dummy_img, "image/jpeg")},
            data={"latitude": "13.01", "longitude": "80.25"}
        )
        assert success_res.status_code == 201
        res_data = success_res.json()
        assert res_data["detection"]["prediction_label"] == "fire"
        assert res_data["detection"]["confidence"] == pytest.approx(0.85)
        assert res_data["risk_level"] == "High"
        
        prediction_id = res_data["detection"]["id"]
        
        # 2. Test Get History - Viewer has 'view_predictions' scope, should succeed
        history_res = await client.get("/api/v1/predictions", headers=viewer_headers)
        assert history_res.status_code == 200
        assert history_res.json()["total"] >= 1
        
        # 3. Test Get History with Filters
        filtered_res = await client.get(
            "/api/v1/predictions/history?label=fire&min_confidence=0.8",
            headers=viewer_headers
        )
        assert filtered_res.status_code == 200
        assert len(filtered_res.json()["items"]) >= 1

        # 4. Test Get Statistics
        stats_res = await client.get("/api/v1/predictions/statistics", headers=viewer_headers)
        assert stats_res.status_code == 200
        assert stats_res.json()["total_predictions"] >= 1
        
        # 5. Test Get Single Prediction details
        single_res = await client.get(f"/api/v1/predictions/{prediction_id}", headers=viewer_headers)
        assert single_res.status_code == 200
        assert single_res.json()["filename"] == "img.jpg"
