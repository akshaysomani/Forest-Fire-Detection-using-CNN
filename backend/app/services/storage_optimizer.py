import io
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.concurrency import run_in_threadpool
from app.repositories.image_repository import (
    image_repository,
    image_storage_location_repository,
)


class StorageOptimizer:
    async def get_shared_location_if_duplicate(self, db: AsyncSession, md5_hash: str) -> str | None:
        """
        Deduplication pooling: check if an identical file MD5 already exists in the database.
        Returns the existing primary file path, so we can avoid writing duplicate files.
        """
        existing = await image_repository.get_by_md5(db, md5_hash)
        if existing:
            loc = await image_storage_location_repository.get_primary_location(db, existing.id)
            if loc:
                return loc.file_key_or_path
        return None

    async def tune_resolution(self, file_bytes: bytes, max_dimension: int = 1920) -> bytes:
        """
        Resolution tuning: downscale oversized image inputs to a sensible ceiling (e.g. 1920px width/height)
        while maintaining aspect ratio. Saves storage space on high-resolution camera feeds.
        """
        def _tune():
            img = Image.open(io.BytesIO(file_bytes))
            width, height = img.size
            
            if width > max_dimension or height > max_dimension:
                # Calculate scale ratio
                ratio = min(max_dimension / width, max_dimension / height)
                new_w = int(width * ratio)
                new_h = int(height * ratio)
                tuned_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                out = io.BytesIO()
                # Maintain original format
                img_format = img.format or "PNG"
                tuned_img.save(out, format=img_format)
                return out.getvalue()
                
            return file_bytes

        return await run_in_threadpool(_tune)


storage_optimizer = StorageOptimizer()
