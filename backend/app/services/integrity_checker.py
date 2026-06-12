import io
import uuid
from typing import BinaryIO, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image
from app.repositories.image_repository import image_repository


class IntegrityChecker:
    @staticmethod
    def verify_pixel_integrity(file_stream: BinaryIO) -> Tuple[bool, str | None]:
        """
        Perform deep verification of the image pixel array.
        Standard Pillow verify() only scans headers; this method forces a full decode.
        """
        try:
            file_stream.seek(0)
            img = Image.open(file_stream)
            img.load()  # Force loading and decoding of pixel data
            file_stream.seek(0)
            return True, None
        except Exception as e:
            return False, f"Pixel data is corrupted or truncated: {str(e)}"

    @staticmethod
    async def check_global_duplication(db: AsyncSession, md5_hash: str) -> Tuple[bool, uuid.UUID | None]:
        """
        Check database for global MD5 duplication.
        Returns (is_duplicate, duplicate_image_id).
        """
        existing = await image_repository.get_by_md5(db, md5_hash)
        if existing:
            return True, existing.id
        return False, None


integrity_checker = IntegrityChecker()
