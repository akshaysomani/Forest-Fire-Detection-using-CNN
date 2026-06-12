import torch
from torchvision import transforms
from typing import Dict, Any, List


class AddGaussianNoise(object):
    def __init__(self, mean: float = 0.0, std: float = 0.05):
        self.mean = mean
        self.std = std

    def __call__(self, tensor: torch.Tensor) -> torch.Tensor:
        return tensor + torch.randn(tensor.size()) * self.std + self.mean

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(mean={self.mean}, std={self.std})"


class AugmentationPipeline:
    @staticmethod
    def get_augmentation_transforms(config: Dict[str, Any] | None = None) -> transforms.Compose:
        """
        Build a composition of torchvision image augmentations based on configuration parameters:
        - horizontal_flip: bool (default True)
        - vertical_flip: bool (default False)
        - rotation_degrees: int (default 15)
        - brightness: float (default 0.1)
        - contrast: float (default 0.1)
        - zoom_scale: tuple (default (0.8, 1.2))
        - noise_std: float (default 0.0)
        """
        if config is None:
            config = {}

        transform_list: List[Any] = []

        # Zoom / Crop
        zoom_scale = config.get("zoom_scale", (0.8, 1.2))
        if zoom_scale:
            # We resize and crop randomly for training data
            transform_list.append(transforms.RandomResizedCrop(size=(224, 224), scale=zoom_scale))
        else:
            transform_list.append(transforms.Resize((224, 224)))

        # Flipping
        if config.get("horizontal_flip", True):
            transform_list.append(transforms.RandomHorizontalFlip())
        if config.get("vertical_flip", False):
            transform_list.append(transforms.RandomVerticalFlip())

        # Rotation
        rotation_degrees = config.get("rotation_degrees", 15)
        if rotation_degrees > 0:
            transform_list.append(transforms.RandomRotation(degrees=rotation_degrees))

        # Color adjustments
        brightness = config.get("brightness", 0.1)
        contrast = config.get("contrast", 0.1)
        if brightness > 0 or contrast > 0:
            transform_list.append(transforms.ColorJitter(brightness=brightness, contrast=contrast))

        # Core operations
        transform_list.append(transforms.ToTensor())

        # Normalization
        mean = config.get("mean", [0.485, 0.456, 0.406])
        std = config.get("std", [0.229, 0.224, 0.225])
        transform_list.append(transforms.Normalize(mean=mean, std=std))

        # Noise Injection
        noise_std = config.get("noise_std", 0.0)
        if noise_std > 0:
            transform_list.append(AddGaussianNoise(std=noise_std))

        return transforms.Compose(transform_list)


augmentation_pipeline = AugmentationPipeline()
