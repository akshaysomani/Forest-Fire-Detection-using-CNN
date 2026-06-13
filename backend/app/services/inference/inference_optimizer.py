import torch
import torch.nn as nn
import logging

logger = logging.getLogger("inference.optimizer")


class InferenceOptimizer:
    @staticmethod
    def optimize_model(model: nn.Module, device: torch.device) -> nn.Module:
        """
        Apply performance optimizations to a PyTorch model for production inference.
        1. Compiles with Torch JIT/Script if possible
        2. Applies FP16 casting if executing on a CUDA GPU
        """
        # Ensure model is in evaluation mode before compilation
        model.eval()

        # 1. GPU CUDA half-precision (FP16) conversion
        # Reduces GPU VRAM consumption by 50% and leverages tensor cores on modern GPUs
        if device.type == "cuda":
            try:
                model = model.half()
                logger.info("Applied FP16 half-precision casting to model for CUDA device execution.")
            except Exception as e:
                logger.warning(f"Failed to cast model to half-precision: {e}. Executing in FP32.")

        # 2. TorchScript trace compilation
        # Traces model structure and compiles graph into TorchScript bytecode for faster evaluation
        try:
            # Create a dummy tensor representing shape (1, 3, 224, 224)
            # Use float16 dummy tensor if model was cast to half-precision
            dummy_input = torch.randn(1, 3, 224, 224).to(device)
            if device.type == "cuda":
                dummy_input = dummy_input.half()
                
            # Perform tracing
            traced_model = torch.jit.trace(model, dummy_input)
            logger.info("Successfully traced CNN model using TorchScript JIT compiler.")
            return traced_model
        except Exception as e:
            logger.warning(f"Could not trace model with Torch JIT: {e}. Falling back to standard PyTorch eager mode execution.")
            return model


inference_optimizer = InferenceOptimizer()
