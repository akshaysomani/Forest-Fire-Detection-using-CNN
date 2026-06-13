import uuid
import logging
from typing import Sequence, Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy import select, func, and_, desc, or_, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.detection import Detection

logger = logging.getLogger("inference.prediction_repository")


class PredictionRepository(BaseRepository[Detection]):
    def __init__(self):
        super().__init__(Detection)

    async def get_filtered_history(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[uuid.UUID] = None,
        prediction_label: Optional[str] = None,
        min_confidence: Optional[float] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_deleted: bool = False
    ) -> Tuple[Sequence[Detection], int]:
        """
        Retrieve a filtered, paginated list of predictions and the total matching record count.
        """
        query = select(self.model)
        count_query = select(func.count()).select_from(self.model)

        filters = []

        if not include_deleted:
            filters.append(self.model.deleted_at.is_(None))
        if user_id:
            filters.append(self.model.user_id == user_id)
        if prediction_label:
            filters.append(self.model.prediction_label == prediction_label)
        if min_confidence is not None:
            filters.append(self.model.confidence >= min_confidence)
        if start_date:
            filters.append(self.model.created_at >= start_date)
        if end_date:
            filters.append(self.model.created_at <= end_date)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # Order by created_at descending by default
        query = query.order_by(desc(self.model.created_at)).offset(skip).limit(limit)

        result = await db.execute(query)
        items = result.scalars().all()

        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        return items, total

    async def calculate_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Compile database-wide prediction telemetry metrics.
        """
        # Exclude deleted detections
        base_filter = self.model.deleted_at.is_(None)

        # Count total, fire, and non-fire
        count_q = select(
            func.count().label("total"),
            func.sum(func.cast(self.model.prediction_label == "fire", Integer)).label("fire"),
            func.sum(func.cast(self.model.prediction_label == "non-fire", Integer)).label("non_fire"),
            func.avg(self.model.confidence).label("avg_conf")
        ).where(base_filter)

        res = await db.execute(count_q)
        row = res.first()

        total = row.total if row and row.total else 0
        fire = row.fire if row and row.fire else 0
        non_fire = row.non_fire if row and row.non_fire else 0
        avg_conf = float(row.avg_conf) if row and row.avg_conf else 0.0

        # Calculate accuracy metrics using human-verified ground truths:
        # A prediction is "correct" if (prediction_label == 'fire' and is_verified_fire == True) OR (prediction_label == 'non-fire' and is_verified_fire == False)
        verified_total_q = select(func.count()).where(
            and_(base_filter, self.model.is_verified_fire.is_not(None))
        )
        verified_total_res = await db.execute(verified_total_q)
        verified_total = verified_total_res.scalar() or 0

        accuracy = None
        if verified_total > 0:
            correct_q = select(func.count()).where(
                and_(
                    base_filter,
                    self.model.is_verified_fire.is_not(None),
                    or_(
                        and_(self.model.prediction_label == "fire", self.model.is_verified_fire == True),
                        and_(self.model.prediction_label == "non-fire", self.model.is_verified_fire == False)
                    )
                )
            )
            correct_res = await db.execute(correct_q)
            correct_count = correct_res.scalar() or 0
            accuracy = (correct_count / verified_total) * 100.0

        return {
            "total_predictions": total,
            "fire_count": fire,
            "non_fire_count": non_fire,
            "average_confidence": avg_conf,
            "accuracy_percentage": accuracy
        }


prediction_repository = PredictionRepository()
