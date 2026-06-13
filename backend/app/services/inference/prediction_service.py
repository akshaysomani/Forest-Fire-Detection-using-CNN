import uuid
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.inference.prediction_engine import prediction_engine
from app.repositories.prediction_repository import prediction_repository
from app.models.detection import Detection
from app.services.activity_logger import activity_logger

logger = logging.getLogger("inference.prediction_service")


class PredictionService:
    @staticmethod
    async def predict_and_store(
        db: AsyncSession,
        file_bytes: bytes,
        filename: str,
        user_id: uuid.UUID,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        image_path: Optional[str] = None
    ) -> Detection:
        """
        Run inference on the image bytes, save the output record to the database,
        and log the classification event in audit trails.
        """
        # 1. Run prediction engine
        prediction_data = await prediction_engine.predict_single_image(db, file_bytes, filename)
        
        # 2. If image_path is not provided, use default placeholder/virtual path
        resolved_image_path = image_path or f"detections/{uuid.uuid4()}_{filename}"

        # 3. Create database record
        detection_record = Detection(
            user_id=user_id,
            image_path=resolved_image_path,
            filename=filename,
            prediction_label=prediction_data["prediction_label"],
            confidence=prediction_data["confidence"],
            model_name=prediction_data["model_name"],
            model_version=prediction_data["model_version"],
            latitude=latitude,
            longitude=longitude,
            is_verified_fire=None,
            alert_sent=False
        )

        # 4. Save to database using repository
        db.add(detection_record)
        await db.flush()  # Populates detection_record.id

        # Trigger alert checks (evaluates if label is fire & confidence >= threshold)
        try:
            from app.services.alert import alert_generator
            await alert_generator.evaluate_detection(db, detection_record)
        except Exception as alert_err:
            logger.error(f"Failed during alert evaluation: {alert_err}", exc_info=True)

        # 5. Log activity audit log
        try:
            activity_logger.log_activity(
                user_id=user_id,
                action="cnn_prediction",
                resource_type="detection",
                resource_id=str(detection_record.id),
                details={
                    "filename": filename,
                    "prediction_label": detection_record.prediction_label,
                    "confidence": detection_record.confidence,
                    "model": detection_record.model_name
                }
            )
        except Exception as log_err:
            logger.warning(f"Failed to write activity audit record: {log_err}")

        logger.info(f"Detection record '{detection_record.id}' successfully saved in database.")
        
        return detection_record


prediction_service = PredictionService()
