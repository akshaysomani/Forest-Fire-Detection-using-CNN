from typing import Dict, Any
from app.services.training.training_config import HyperparametersConfig


class HyperparameterManager:
    @staticmethod
    def validate_and_parse(hparams: Dict[str, Any] | None) -> HyperparametersConfig:
        """Parse dictionary and validate hyperparameters config."""
        if hparams is None:
            return HyperparametersConfig()
        return HyperparametersConfig(**hparams)

    @staticmethod
    def serialize(config: HyperparametersConfig) -> Dict[str, Any]:
        """Serialize configuration back into dictionary format."""
        return config.model_dump()


hyperparameter_manager = HyperparameterManager()
