import torch
import torch.nn as nn
import logging
from typing import Tuple

logger = logging.getLogger("inference.prediction_executor")


class PredictionExecutor:
    @staticmethod
    def execute_inference(model: nn.Module, input_tensor: torch.Tensor, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Execute forward pass of the neural network on the specified device.
        Ensures execution occurs in evaluation mode with gradient calculation disabled.
        Returns a tuple of (logits, probabilities).
        """
        # 1. Ensure model is in evaluation mode (disable dropout, batchnorm updates)
        model.eval()
        
        # 2. Push input tensor to target hardware (GPU or CPU fallback)
        tensor_on_device = input_tensor.to(device)

        # 3. Disable gradient compilation to reduce memory consumption and maximize performance
        with torch.no_grad():
            try:
                logits = model(tensor_on_device)
                
                # Apply softmax to calculate confidence probabilities for each class
                probabilities = torch.softmax(logits, dim=1)
                
                return logits.cpu(), probabilities.cpu()
            except Exception as e:
                logger.error(f"Execution forward pass failed on device '{device}': {e}")
                
                # Automatic CPU Fallback if GPU execution fails
                if device.type == "cuda":
                    logger.warning("CUDA execution failed. Falling back to CPU for inference.")
                    cpu_device = torch.device("cpu")
                    # Push model and tensor to CPU
                    model.to(cpu_device)
                    tensor_on_cpu = input_tensor.to(cpu_device)
                    try:
                        logits = model(tensor_on_cpu)
                        probabilities = torch.softmax(logits, dim=1)
                        return logits.cpu(), probabilities.cpu()
                    except Exception as cpu_err:
                        logger.error(f"CPU Fallback execution also failed: {cpu_err}")
                        raise cpu_err
                raise e


prediction_executor = PredictionExecutor()
