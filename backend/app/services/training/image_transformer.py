import io
from PIL import Image
from typing import Tuple


class ImageTransformer:
    @staticmethod
    def preprocess_image_bytes(file_bytes: bytes, target_size: Tuple[int, int] = (224, 224)) -> Image.Image:
        """Helper to open bytes, convert to RGB, and resize to target dimension using bilinear filtering."""
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        return img.resize(target_size, Image.Resampling.BILINEAR)


image_transformer = ImageTransformer()
