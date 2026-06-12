import io
from typing import BinaryIO, Tuple
from PIL import Image


class ImageValidator:
    @staticmethod
    def verify_magic_bytes(file_stream: BinaryIO) -> Tuple[bool, str | None]:
        """
        Verify file magic bytes to detect extension spoofing.
        Returns (is_valid, detected_mime_type).
        """
        try:
            file_stream.seek(0)
            header = file_stream.read(12)
            file_stream.seek(0)
        except Exception as e:
            return False, None

        if len(header) < 4:
            return False, None

        # Check PNG: 89 50 4E 47 0D 0A 1A 0A
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return True, "image/png"

        # Check JPEG/JPG: FF D8 FF
        if header.startswith(b"\xff\xd8\xff"):
            return True, "image/jpeg"

        # Check WEBP: RIFF (bytes 0-3) and WEBP (bytes 8-11)
        if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            return True, "image/webp"

        # Check GIF: GIF87a or GIF89a
        if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
            return True, "image/gif"

        return False, None


image_validator = ImageValidator()
