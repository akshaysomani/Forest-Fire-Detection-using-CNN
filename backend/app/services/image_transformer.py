import io
from typing import List, Tuple
from PIL import Image, ImageEnhance
from fastapi.concurrency import run_in_threadpool


class ImageTransformer:
    @staticmethod
    def normalize_pixels(file_bytes: bytes, target_size: Tuple[int, int] = (224, 224)) -> List[float]:
        """
        Normalize image pixels to range [0.0, 1.0].
        Resizes to target_size first, converts to RGB, and returns a flat float array.
        This provides a standardized representation directly ingestible by CNNs.
        """
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        img = img.resize(target_size, Image.Resampling.BILINEAR)

        # Extract pixel data and scale
        pixel_bytes = img.tobytes()
        return [b / 255.0 for b in pixel_bytes]

    async def augment_image(self, file_bytes: bytes, action: str) -> bytes:
        """
        Apply a safe augmentation transform to the image.
        Supported actions: 'flip_horizontal', 'flip_vertical', 'rotate_90', 'rotate_180', 'enhance_contrast'
        """

        def _augment():
            img = Image.open(io.BytesIO(file_bytes))

            if action == "flip_horizontal":
                augmented = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            elif action == "flip_vertical":
                augmented = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            elif action == "rotate_90":
                augmented = img.transpose(Image.Transpose.ROTATE_90)
            elif action == "rotate_180":
                augmented = img.transpose(Image.Transpose.ROTATE_180)
            elif action == "enhance_contrast":
                enhancer = ImageEnhance.Contrast(img)
                augmented = enhancer.enhance(1.5)
            else:
                augmented = img

            out = io.BytesIO()
            augmented.save(out, format="PNG")
            return out.getvalue()

        return await run_in_threadpool(_augment)


image_transformer = ImageTransformer()
