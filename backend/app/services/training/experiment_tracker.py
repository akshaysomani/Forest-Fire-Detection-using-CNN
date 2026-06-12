from typing import Dict, Any, List
from app.services.training.training_logger import training_logger
from app.services.training.artifact_manager import artifact_manager


class ExperimentTracker:
    @staticmethod
    async def log_epoch(
        run_id: str,
        epoch: int,
        train_loss: float,
        train_acc: float,
        val_loss: float,
        val_acc: float,
        lr: float
    ) -> Dict[str, Any]:
        """Log epoch progress to stdout and return log details."""
        metrics = {
            "epoch": epoch,
            "train_loss": round(train_loss, 5),
            "train_acc": round(train_acc, 5),
            "val_loss": round(val_loss, 5),
            "val_acc": round(val_acc, 5),
            "learning_rate": lr
        }

        training_logger.info(
            run_id=run_id,
            message=f"Epoch {epoch} Completed: train_loss={train_loss:.4f}, train_acc={train_acc:.4f}, val_loss={val_loss:.4f}, val_acc={val_acc:.4f}",
            extra=metrics
        )
        return metrics

    @staticmethod
    async def save_run_metadata(
        run_id: str,
        hyperparameters: Dict[str, Any],
        metrics_history: List[Dict[str, Any]],
        evaluation_summary: Dict[str, Any] | None = None
    ) -> None:
        """Saves hyperparameters, metrics, and evaluation summaries to storage as JSON artifacts."""
        await artifact_manager.save_config(run_id, hyperparameters)
        await artifact_manager.save_metrics(run_id, metrics_history)
        if evaluation_summary:
            await artifact_manager.save_evaluation_report_json(run_id, evaluation_summary)


experiment_tracker = ExperimentTracker()
