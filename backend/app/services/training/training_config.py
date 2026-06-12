from pydantic import BaseModel, Field, field_validator
from typing import Literal


class HyperparametersConfig(BaseModel):
    learning_rate: float = Field(default=0.001, gt=0.0, le=0.1, description="Learning rate for model optimizer")
    batch_size: int = Field(default=32, description="Batch size for training and validation loaders")
    epochs: int = Field(default=10, ge=1, le=100, description="Number of training epochs")
    optimizer: Literal["sgd", "adam", "adamw"] = Field(default="adam", description="Optimizer type")
    dropout: float = Field(default=0.5, ge=0.0, lt=1.0, description="Dropout rate for fully connected layers")
    weight_decay: float = Field(default=1e-4, ge=0.0, le=0.1, description="Weight decay (L2 regularization)")
    random_seed: int = Field(default=42, ge=0, description="Random seed for reproducibility")

    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        if v <= 0 or (v & (v - 1)) != 0:
            raise ValueError("batch_size must be a positive power of 2 (e.g., 16, 32, 64, 128)")
        return v
