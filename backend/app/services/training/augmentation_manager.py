from typing import Dict, Any
from torchvision import transforms
from app.services.training.augmentation_pipeline import augmentation_pipeline


class AugmentationManager:
    @staticmethod
    def get_transforms(policy: str = "default", custom_config: Dict[str, Any] | None = None) -> transforms.Compose:
        """
        Get augmented torchvision Compose object based on selected policy:
        - none: Resizing only. No spatial or color changes.
        - light: Basic flips, light rotation, minor color shifts.
        - default: Standard flips, average rotation, moderate color shifts.
        - heavy: Multi-directional flips, larger rotations, color jitter, zoom, and noise injection.
        """
        policy = policy.lower().strip()

        if policy == "none":
            config = {
                "zoom_scale": None,
                "horizontal_flip": False,
                "vertical_flip": False,
                "rotation_degrees": 0,
                "brightness": 0.0,
                "contrast": 0.0,
                "noise_std": 0.0
            }
        elif policy == "light":
            config = {
                "zoom_scale": (0.9, 1.1),
                "horizontal_flip": True,
                "vertical_flip": False,
                "rotation_degrees": 10,
                "brightness": 0.05,
                "contrast": 0.05,
                "noise_std": 0.0
            }
        elif policy == "heavy":
            config = {
                "zoom_scale": (0.7, 1.3),
                "horizontal_flip": True,
                "vertical_flip": True,
                "rotation_degrees": 30,
                "brightness": 0.2,
                "contrast": 0.2,
                "noise_std": 0.05
            }
        else:  # default
            config = {
                "zoom_scale": (0.8, 1.2),
                "horizontal_flip": True,
                "vertical_flip": False,
                "rotation_degrees": 15,
                "brightness": 0.1,
                "contrast": 0.1,
                "noise_std": 0.0
            }

        # Apply overrides
        if custom_config:
            config.update(custom_config)

        return augmentation_pipeline.get_augmentation_transforms(config)


augmentation_manager = AugmentationManager()
