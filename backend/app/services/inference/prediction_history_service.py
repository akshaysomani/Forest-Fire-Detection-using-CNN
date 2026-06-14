import uuid
import logging
from typing import Sequence, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.prediction_repository import prediction_repository
from app.models.detection import Detection
from app.core.exceptions import EntityNotFoundException

logger = logging.getLogger("inference.prediction_history_service")


class PredictionHistoryService:
    @staticmethod
    async def get_history(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[uuid.UUID] = None,
        prediction_label: Optional[str] = None,
        min_confidence: Optional[float] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[Sequence[Detection], int]:
        """
        Query prediction history from the database using filters.
        """
        logger.info(f"Fetching prediction history (skip={skip}, limit={limit}). Filters: label={prediction_label}")
        return await prediction_repository.get_filtered_history(
            db=db,
            skip=skip,
            limit=limit,
            user_id=user_id,
            prediction_label=prediction_label,
            min_confidence=min_confidence,
            start_date=start_date,
            end_date=end_date,
        )

    @staticmethod
    async def get_by_id(db: AsyncSession, prediction_id: uuid.UUID) -> Detection:
        """
        Retrieve a single prediction by ID. Raises EntityNotFoundException if not found.
        """
        prediction = await prediction_repository.get_by_id(db, prediction_id)
        if not prediction or prediction.deleted_at is not None:
            logger.warning(f"Prediction result not found: {prediction_id}")
            raise EntityNotFoundException(f"Prediction result with ID '{prediction_id}' not found.")
        return prediction

    @staticmethod
    async def get_statistics(db: AsyncSession) -> Dict[str, Any]:
        """
        Compile performance and volume statistics for predictions.
        """
        logger.info("Computing prediction telemetry statistics.")
        return await prediction_repository.calculate_statistics(db)


prediction_history_service = PredictionHistoryService()
