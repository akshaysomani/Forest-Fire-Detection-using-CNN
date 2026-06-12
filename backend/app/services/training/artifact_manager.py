import json
from typing import Dict, Any, List
from app.services.storage_service import storage_service


class ArtifactManager:
    @staticmethod
    async def save_config(run_id: str, config_dict: Dict[str, Any]) -> str:
        """Saves hyperparameters config dict as JSON."""
        config_bytes = json.dumps(config_dict, indent=4).encode("utf-8")
        path = f"runs/{run_id}/artifacts/config.json"
        await storage_service.save_file(config_bytes, path)
        return path

    @staticmethod
    async def save_metrics(run_id: str, metrics_history: List[Dict[str, Any]]) -> str:
        """Saves epoch-by-epoch loss/accuracy metrics as JSON."""
        metrics_bytes = json.dumps(metrics_history, indent=4).encode("utf-8")
        path = f"runs/{run_id}/artifacts/metrics.json"
        await storage_service.save_file(metrics_bytes, path)
        return path

    @staticmethod
    async def save_evaluation_report_json(run_id: str, metrics_summary: Dict[str, Any]) -> str:
        """Saves final evaluation metrics summary as JSON."""
        summary_bytes = json.dumps(metrics_summary, indent=4).encode("utf-8")
        path = f"runs/{run_id}/artifacts/evaluation_report.json"
        await storage_service.save_file(summary_bytes, path)
        return path


artifact_manager = ArtifactManager()
