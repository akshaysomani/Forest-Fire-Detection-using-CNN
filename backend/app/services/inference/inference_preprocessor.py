import io
import logging
from PIL import Image
from fastapi.concurrency import run_in_threadpool
from app.core.exceptions import ValidationException

logger = logging.getLogger("inference.preprocessor")


class InferencePreprocessor:
    @staticmethod
    async def preprocess_image(
        file_bytes: bytes,
        target_size: tuple[int, int] = (224, 224)
    ) -> Image.Image:
        """
        Resize image, handle transparency channels (convert RGBA to RGB), and return PIL Image.
        Runs operations in threadpool to prevent blocking the event loop.
        """
        def _process():
            try:
                img = Image.open(io.BytesIO(file_bytes))
                
                # Convert transparency to solid background (white) or just convert RGBA -> RGB
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    # Create white background canvas
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    # Paste source image onto canvas using alpha channel mask
                    background.paste(img, mask=img.convert("RGBA").split()[3])
                    img = background
                else:
                    img = img.convert("RGB")

                # Resize using high-quality Lanczos resampling
                img = img.resize(target_size, Image.Resampling.LANCZOS)
                return img
            except Exception as e:
                logger.error(f"Failed preprocessing image: {e}")
                raise ValidationException(f"Image preprocessing failed: {str(e)}")

        return await run_in_threadpool(_process)


inference_preprocessor = InferencePreprocessor()
