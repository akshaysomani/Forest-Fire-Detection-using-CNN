import torch
import torch.nn as nn
import torchvision.models as models
from app.services.training.cnn_model import CustomCNN


class ModelFactory:
    @staticmethod
    def create_model(
        model_name: str,
        num_classes: int = 2,
        pretrained: bool = True,
        dropout: float = 0.5
    ) -> nn.Module:
        """
        Build and configure a PyTorch classification model.
        Supports: custom_cnn, resnet18, resnet50, mobilenet_v3, efficientnet_b0.
        """
        model_name = model_name.lower().strip()

        if model_name == "custom_cnn":
            return CustomCNN(num_classes=num_classes, dropout=dropout)

        elif model_name == "resnet18":
            weights = models.ResNet18_Weights.DEFAULT if pretrained else None
            model = models.resnet18(weights=weights)
            in_features = model.fc.in_features
            model.fc = nn.Sequential(
                nn.Dropout(p=dropout),
                nn.Linear(in_features, num_classes)
            )
            return model

        elif model_name == "resnet50":
            weights = models.ResNet50_Weights.DEFAULT if pretrained else None
            model = models.resnet50(weights=weights)
            in_features = model.fc.in_features
            model.fc = nn.Sequential(
                nn.Dropout(p=dropout),
                nn.Linear(in_features, num_classes)
            )
            return model

        elif model_name == "mobilenet_v3":
            weights = models.MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
            model = models.mobilenet_v3_small(weights=weights)
            # MobileNet V3 Small classifier is a Sequential:
            # Linear -> Hardswish -> Dropout -> Linear
            # We replace the final Linear layer (index 3)
            in_features = model.classifier[3].in_features
            model.classifier[3] = nn.Linear(in_features, num_classes)
            return model

        elif model_name == "efficientnet_b0":
            weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
            model = models.efficientnet_b0(weights=weights)
            # EfficientNet B0 classifier is a Sequential:
            # Dropout -> Linear
            # We replace the final Linear layer (index 1)
            in_features = model.classifier[1].in_features
            model.classifier[1] = nn.Linear(in_features, num_classes)
            return model

        else:
            raise ValueError(
                f"Unsupported model architecture '{model_name}'. "
                f"Choose from: custom_cnn, resnet18, resnet50, mobilenet_v3, efficientnet_b0."
            )


model_factory = ModelFactory()
