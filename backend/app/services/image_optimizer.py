import io
from PIL import Image
from fastapi.concurrency import run_in_threadpool


class ImageOptimizer:
    @staticmethod
    async def optimize_and_compress(
        file_bytes: bytes,
        quality: int = 80,
        target_format: str = "WEBP"
    ) -> bytes:
        """
        Optimize and compress image bytes.
        Strips EXIF data and metadata to minimize file footprint.
        Runs in background thread pool.
        """
        def _optimize():
            img = Image.open(io.BytesIO(file_bytes))
            
            # Convert RGBA/LA modes to RGB if target format does not support transparency
            if target_format.upper() in ("JPEG", "JPG") and img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")

            out = io.BytesIO()
            # Saving without passing 'exif=img.info.get("exif")' strips the metadata
            img.save(out, format=target_format, quality=quality)
            return out.getvalue()

        return await run_in_threadpool(_optimize)


image_optimizer = ImageOptimizer()
