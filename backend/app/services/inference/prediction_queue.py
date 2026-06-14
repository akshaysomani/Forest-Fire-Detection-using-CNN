import asyncio
import uuid
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("inference.prediction_queue")


class BatchJobState:
    def __init__(self, job_id: uuid.UUID, total_images: int):
        self.job_id = job_id
        self.status = "pending"  # pending, processing, completed, failed
        self.total_count = total_images
        self.success_count = 0
        self.failed_count = 0
        self.results: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": str(self.job_id),
            "status": self.status,
            "total_count": self.total_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "results": self.results,
            "errors": self.errors,
        }


class PredictionQueue:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._jobs: Dict[uuid.UUID, BatchJobState] = {}
        logger.info("Initialized async Batch PredictionQueue.")

    async def enqueue_job(self, user_id: uuid.UUID, images: List[Dict[str, Any]]) -> uuid.UUID:
        """
        Register a new batch prediction job and queue its items.
        Each image dict should contain: 'filename', 'file_bytes', and optional 'latitude', 'longitude'.
        """
        job_id = uuid.uuid4()
        job_state = BatchJobState(job_id, len(images))
        self._jobs[job_id] = job_state

        # Enqueue item by item
        for idx, img in enumerate(images):
            task_item = {
                "job_id": job_id,
                "task_index": idx,
                "user_id": user_id,
                "filename": img["filename"],
                "file_bytes": img["file_bytes"],
                "latitude": img.get("latitude"),
                "longitude": img.get("longitude"),
                "image_path": img.get("image_path"),
            }
            await self._queue.put(task_item)

        logger.info(f"Enqueued Batch Job '{job_id}' with {len(images)} tasks.")
        return job_id

    async def dequeue_task(self) -> Dict[str, Any]:
        """Fetch the next task from the queue."""
        return await self._queue.get()

    def task_done(self) -> None:
        """Mark task as done in the queue."""
        self._queue.task_done()

    def get_job_status(self, job_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Retrieve status parameters of a queued job."""
        if job_id in self._jobs:
            return self._jobs[job_id].to_dict()
        return None

    def update_job_success(self, job_id: uuid.UUID, result: Dict[str, Any]) -> None:
        """Record success of a single task in a job."""
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.status = "processing"
            job.success_count += 1
            job.results.append(result)
            self._check_job_completion(job)

    def update_job_failure(self, job_id: uuid.UUID, filename: str, error_msg: str) -> None:
        """Record failure of a single task in a job."""
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.status = "processing"
            job.failed_count += 1
            job.errors.append({"filename": filename, "error": error_msg})
            self._check_job_completion(job)

    def _check_job_completion(self, job: BatchJobState) -> None:
        """Verify if all images in the batch have been processed."""
        processed = job.success_count + job.failed_count
        if processed >= job.total_count:
            job.status = "completed"
            logger.info(
                f"Batch Job '{job.job_id}' has completed processing. Success={job.success_count}, Failures={job.failed_count}"
            )


prediction_queue = PredictionQueue()
