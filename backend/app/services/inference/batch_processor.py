import asyncio
import logging
from typing import Optional
from app.core.database import SessionLocal
from app.services.inference.prediction_queue import prediction_queue
from app.services.inference.prediction_service import prediction_service

logger = logging.getLogger("inference.batch_processor")


class BatchProcessor:
    def __init__(self):
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False

    def start_worker(self) -> None:
        """Boot background worker if not already running."""
        if self._worker_task is None or self._worker_task.done():
            self._running = True
            self._worker_task = asyncio.create_task(self._worker_loop())
            logger.info("BatchProcessor background worker started.")

    def stop_worker(self) -> None:
        """Gracefully stop background processing worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            logger.info("BatchProcessor background worker stop requested.")

    async def _worker_loop(self) -> None:
        """Continuous consumer loop executing enqueued tasks."""
        while self._running:
            try:
                task = await prediction_queue.dequeue_task()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error dequeuing task: {e}")
                await asyncio.sleep(1)
                continue

            job_id = task["job_id"]
            filename = task["filename"]
            user_id = task["user_id"]
            file_bytes = task["file_bytes"]
            latitude = task["latitude"]
            longitude = task["longitude"]
            image_path = task["image_path"]

            logger.info(f"Processing task for job '{job_id}': '{filename}'")

            async with SessionLocal() as db:
                try:
                    detection = await prediction_service.predict_and_store(
                        db=db,
                        file_bytes=file_bytes,
                        filename=filename,
                        user_id=user_id,
                        latitude=latitude,
                        longitude=longitude,
                        image_path=image_path
                    )
                    await db.commit()
                    
                    # Log success details
                    prediction_queue.update_job_success(
                        job_id=job_id,
                        result={
                            "detection_id": str(detection.id),
                            "filename": filename,
                            "prediction_label": detection.prediction_label,
                            "confidence": detection.confidence
                        }
                    )
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Failed to process task in batch job '{job_id}' for image '{filename}': {e}")
                    prediction_queue.update_job_failure(
                        job_id=job_id,
                        filename=filename,
                        error_msg=str(e)
                    )
                finally:
                    prediction_queue.task_done()


# Initialize global worker instance
batch_processor = BatchProcessor()
