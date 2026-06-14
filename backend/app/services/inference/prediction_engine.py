import time
import logging
from typing import Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.inference.input_validator import input_validator
from app.services.inference.inference_preprocessor import inference_preprocessor
from app.services.inference.prediction_transformer import prediction_transformer
from app.services.inference.prediction_executor import prediction_executor
from app.services.inference.model_manager import model_manager
from app.services.inference.classification_service import classification_service
from app.services.inference.risk_analyzer import risk_analyzer
from app.services.inference.prediction_mapper import prediction_mapper

logger = logging.getLogger("inference.prediction_engine")


class PredictionEngine:
    @staticmethod
    async def predict_single_image(db: AsyncSession, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Run inference pipeline on a single image.
        1. Validate inputs
        2. Preprocess & transform image
        3. Load active model
        4. Execute forward pass
        5. Map classes and assess risk
        Returns a dictionary of mapped results.
        """
        start_time = time.perf_counter()

        # 1. Validation
        input_validator.validate_image_bytes(file_bytes, filename)

        # 2. Preprocess to PIL image
        pil_image = await inference_preprocessor.preprocess_image(file_bytes)

        # 3. Transform to tensor
        input_tensor = prediction_transformer.transform_image(pil_image)

        # 4. Resolve active model and details
        model, model_name, model_version = await model_manager.get_active_model(db)
        device = model_manager.device

        # 5. Execute inference
        logits, probabilities = prediction_executor.execute_inference(model, input_tensor, device)

        # 6. Extract classification labels and scores
        # probabilities has shape (1, num_classes)
        prob_list = probabilities[0].tolist()

        # Call classification service to resolve label and confidence
        label, confidence = classification_service.resolve_classification(prob_list)

        # 7. Compute risk assessment zones
        risk_level = risk_analyzer.analyze_risk(label, confidence)

        # 8. Map to standardized schema structure
        processing_duration = time.perf_counter() - start_time

        result = prediction_mapper.format_prediction_output(
            model_name=model_name,
            model_version=model_version,
            filename=filename,
            label=label,
            confidence=confidence,
            probabilities=prob_list,
            risk_level=risk_level,
            processing_duration=processing_duration,
        )

        logger.info(
            f"Prediction completed for '{filename}': Label='{label}', "
            f"Confidence={confidence:.4f}, Latency={processing_duration*1000:.2f}ms"
        )
        return result


prediction_engine = PredictionEngine()
