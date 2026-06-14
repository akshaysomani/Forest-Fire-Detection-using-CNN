import io
from typing import Tuple
from PIL import Image
from fastapi.concurrency import run_in_threadpool


class ThumbnailService:
    @staticmethod
    async def generate_thumbnail(file_bytes: bytes, size: Tuple[int, int] = (128, 128), format: str = "WEBP") -> bytes:
        """
        Generate a compressed WebP/PNG thumbnail for fast rendering.
        Runs in a background thread to prevent event-loop blocking.
        """

        def _gen():
            img = Image.open(io.BytesIO(file_bytes))
            # Create a thumbnail maintaining aspect ratio
            img.thumbnail(size, Image.Resampling.LANCZOS)

            out = io.BytesIO()
            # Handle RGBA/transparency for conversion to other formats if required
            if format.upper() in ("JPEG", "JPG") and img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")

            img.save(out, format=format, quality=75)
            return out.getvalue()

        return await run_in_threadpool(_gen)


thumbnail_service = ThumbnailService()
