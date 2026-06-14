import torch
import torchvision.transforms.functional as TF
from PIL import Image
import logging

logger = logging.getLogger("inference.prediction_transformer")


class PredictionTransformer:
    # Standard ImageNet mean and std dev values for ResNet / EfficientNet models
    IMAGENET_MEAN = [0.485, 0.456, 0.406]
    IMAGENET_STD = [0.229, 0.224, 0.225]

    @staticmethod
    def transform_image(img: Image.Image) -> torch.Tensor:
        """
        Convert PIL Image to PyTorch tensor, normalize it, and add batch dimension.
        Returns a tensor of shape (1, 3, height, width).
        """
        # 1. Convert to tensor: Scales channels to [0.0, 1.0], swaps channels from HWC to CHW
        tensor = TF.to_tensor(img)

        # 2. Normalize using ImageNet statistics
        tensor = TF.normalize(tensor, mean=PredictionTransformer.IMAGENET_MEAN, std=PredictionTransformer.IMAGENET_STD)

        # 3. Add batch dimension: shape (3, H, W) -> (1, 3, H, W)
        tensor = tensor.unsqueeze(0)

        return tensor


prediction_transformer = PredictionTransformer()
