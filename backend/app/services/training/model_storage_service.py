class ModelStorageService:
    @staticmethod
    def get_run_dir(run_id: str) -> str:
        """Returns the base storage directory for a specific training run."""
        return f"runs/{run_id}"

    @staticmethod
    def get_checkpoints_dir(run_id: str) -> str:
        """Returns the checkpoints storage directory for a specific training run."""
        return f"runs/{run_id}/checkpoints"

    @staticmethod
    def get_artifacts_dir(run_id: str) -> str:
        """Returns the evaluation report and configurations storage directory for a run."""
        return f"runs/{run_id}/artifacts"


model_storage_service = ModelStorageService()
