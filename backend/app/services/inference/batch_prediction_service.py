import uuid
import logging
from typing import List, Dict, Any, Optional
from app.services.inference.prediction_queue import prediction_queue
from app.services.inference.batch_processor import batch_processor

logger = logging.getLogger("inference.batch_prediction_service")


class BatchPredictionService:
    @staticmethod
    async def submit_batch(user_id: uuid.UUID, images: List[Dict[str, Any]]) -> uuid.UUID:
        """
        Submit a batch of images for background inference.
        Ensures the background processor worker is running, enqueues the tasks,
        and returns the unique Batch Job ID.
        """
        # Ensure worker is alive
        batch_processor.start_worker()

        # Enqueue job
        job_id = await prediction_queue.enqueue_job(user_id=user_id, images=images)
        logger.info(f"Batch prediction job '{job_id}' successfully submitted by user '{user_id}'.")

        return job_id

    @staticmethod
    def get_batch_status(job_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Retrieve progress and results of a submitted batch job."""
        return prediction_queue.get_job_status(job_id)


batch_prediction_service = BatchPredictionService()
