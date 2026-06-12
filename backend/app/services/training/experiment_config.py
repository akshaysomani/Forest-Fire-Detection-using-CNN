import os
from pydantic_settings import BaseSettings


class ExperimentConfig(BaseSettings):
    RUNS_OUTPUT_DIR: str = "./storage/runs"
    LOGS_OUTPUT_DIR: str = "./storage/runs/logs"
    MAX_CHECKPOINTS_TO_KEEP: int = 3
    DEFAULT_LOG_INTERVAL: int = 10  # Log training metrics every N batches

    model_config = {
        "env_prefix": "ML_",
        "extra": "ignore"
    }


experiment_config = ExperimentConfig()
