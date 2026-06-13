from pydantic import BaseModel
from typing import Dict, Any


class ModelRegistryMetrics(BaseModel):
    total_model_families: int
    total_model_versions: int
    active_deployments: int
    staging_deployments: int
    production_deployments: int
    pending_approvals: int
    state_distribution: Dict[str, int]
    deployment_frequency_days: float
    average_approval_time_seconds: float
