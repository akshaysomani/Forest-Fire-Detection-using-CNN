import io
import logging
import torch
import torch.nn as nn
from typing import Dict, Any, Tuple
from app.services.training.model_factory import model_factory
from app.services.storage_service import storage_service
from app.core.exceptions import BaseAPIException

logger = logging.getLogger("inference.model_loader")


class ModelLoadException(BaseAPIException):
    status_code = 500
    error_code = "MODEL_LOAD_ERROR"
    message = "Failed to instantiate or load CNN model."


class ModelLoader:
    @staticmethod
    async def load_model_from_checkpoint(
        model_name: str,
        checkpoint_path: str,
        device: torch.device,
        num_classes: int = 2
    ) -> nn.Module:
        """
        Load a model checkpoint from storage and restore its state dictionary.
        Validates model name and weights shape prior to loading.
        """
        logger.info(f"Loading model '{model_name}' from checkpoint: {checkpoint_path} on device: {device}")
        
        try:
            # 1. Instantiate the base model structure
            model = model_factory.create_model(model_name=model_name, num_classes=num_classes, pretrained=False)
            model.to(device)
        except Exception as e:
            logger.error(f"Failed to create model base structure for '{model_name}': {e}")
            raise ModelLoadException(f"Unsupported or invalid model type: {model_name}. Details: {str(e)}")

        try:
            # 2. Fetch checkpoint bytes from storage
            checkpoint_bytes = await storage_service.read_file(checkpoint_path)
            buffer = io.BytesIO(checkpoint_bytes)
            
            # 3. Load checkpoint state
            checkpoint_data = torch.load(buffer, map_location=device)
            
            # Support both raw state_dicts and wrapped checkpoint dictionary configurations
            if isinstance(checkpoint_data, dict) and "model_state_dict" in checkpoint_data:
                state_dict = checkpoint_data["model_state_dict"]
            elif isinstance(checkpoint_data, dict):
                state_dict = checkpoint_data
            else:
                raise ValueError("Checkpoint format is unrecognized (neither state_dict dict nor wrapped structure found).")
            
            # 4. Validate state dict compatibility
            ModelLoader.validate_state_dict(model, state_dict)
            
            # 5. Load weights
            model.load_state_dict(state_dict)
            model.eval()  # Enforce evaluation mode (disables dropout, batch norm updates)
            
            logger.info(f"Successfully loaded and validated model '{model_name}' weights from checkpoint.")
            return model
            
        except Exception as e:
            logger.error(f"Failed to load state dictionary into model '{model_name}' from path '{checkpoint_path}': {e}")
            raise ModelLoadException(f"Failed to restore checkpoint weights: {str(e)}")

    @staticmethod
    def validate_state_dict(model: nn.Module, state_dict: Dict[str, Any]) -> None:
        """
        Verify that all keys in the model's state_dict exist in the loaded state_dict,
        and that their tensor shapes match precisely to prevent runtime shape mismatch crashes.
        """
        model_state = model.state_dict()
        
        # Check missing or unexpected keys
        missing_keys = set(model_state.keys()) - set(state_dict.keys())
        unexpected_keys = set(state_dict.keys()) - set(model_state.keys())
        
        if missing_keys:
            logger.warning(f"State dict missing keys: {missing_keys}")
        if unexpected_keys:
            logger.warning(f"State dict contains unexpected keys: {unexpected_keys}")
            
        # Check shape alignment
        for key, model_tensor in model_state.items():
            if key in state_dict:
                loaded_tensor = state_dict[key]
                if model_tensor.shape != loaded_tensor.shape:
                    raise ValueError(
                        f"Weight shape mismatch for layer '{key}': "
                        f"Model shape is {model_tensor.shape}, checkpoint shape is {loaded_tensor.shape}."
                    )


model_loader = ModelLoader()
