from pydantic import BaseModel
from typing import Dict, Tuple


class ModelArchitectureInfo(BaseModel):
    name: str
    input_shape: Tuple[int, int, int] = (3, 224, 224)
    description: str
    is_pretrained_supported: bool


SUPPORTED_MODELS: Dict[str, ModelArchitectureInfo] = {
    "custom_cnn": ModelArchitectureInfo(
        name="custom_cnn",
        input_shape=(3, 224, 224),
        description="Shallow Custom CNN with 3 Conv layers, BatchNorm, MaxPooling, and Dropout.",
        is_pretrained_supported=False,
    ),
    "resnet18": ModelArchitectureInfo(
        name="resnet18",
        input_shape=(3, 224, 224),
        description="ResNet-18 Deep Residual Network (supports pre-trained Transfer Learning).",
        is_pretrained_supported=True,
    ),
    "resnet50": ModelArchitectureInfo(
        name="resnet50",
        input_shape=(3, 224, 224),
        description="ResNet-50 Deep Residual Network (supports pre-trained Transfer Learning).",
        is_pretrained_supported=True,
    ),
    "mobilenet_v3": ModelArchitectureInfo(
        name="mobilenet_v3",
        input_shape=(3, 224, 224),
        description="MobileNetV3 (lightweight model designed for edge devices and fast training).",
        is_pretrained_supported=True,
    ),
    "efficientnet_b0": ModelArchitectureInfo(
        name="efficientnet_b0",
        input_shape=(3, 224, 224),
        description="EfficientNet-B0 (advanced architecture optimizing parameter counts and accuracy).",
        is_pretrained_supported=True,
    ),
}
