from torchvision import transforms
from typing import Dict, Any


class PreprocessingPipeline:
    @staticmethod
    def get_preprocessing_transforms(config: Dict[str, Any] | None = None) -> transforms.Compose:
        """
        Build standard preprocessing transforms:
        - Resize to (224, 224)
        - Convert to PyTorch Tensor
        - Standard ImageNet normalization (or custom dataset channel mean/std)
        """
        if config is None:
            config = {}

        mean = config.get("mean", [0.485, 0.456, 0.406])
        std = config.get("std", [0.229, 0.224, 0.225])

        return transforms.Compose(
            [transforms.Resize((224, 224)), transforms.ToTensor(), transforms.Normalize(mean=mean, std=std)]
        )


preprocessing_pipeline = PreprocessingPipeline()
