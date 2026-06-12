import io
from typing import BinaryIO, Tuple
from PIL import Image
from app.services.file_manager import file_manager


class FileValidator:
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

    @staticmethod
    def validate_image(
        file_stream: BinaryIO,
        filename: str,
        mime_type: str | None = None,
        max_size_bytes: int = 10 * 1024 * 1024,  # 10MB Default
        min_resolution: Tuple[int, int] = (128, 128),
        max_resolution: Tuple[int, int] = (8192, 8192),
    ) -> Tuple[bool, str | None, int | None, int | None]:
        """
        Validate an image file:
        - Check extension
        - Check size limits
        - Parse image header to verify resolution boundaries
        - Decode check to ensure the file is not corrupted
        Returns (is_valid, error_message, width, height)
        """
        # 1. Validate extension
        ext = file_manager.get_file_extension(filename)
        if ext not in FileValidator.ALLOWED_EXTENSIONS:
            return False, f"Unsupported file extension: '{ext}'. Allowed extensions are: {list(FileValidator.ALLOWED_EXTENSIONS)}", None, None

        # 2. Validate mime type if provided
        if mime_type and mime_type.lower() not in FileValidator.ALLOWED_MIME_TYPES:
            return False, f"Unsupported mime type: '{mime_type}'. Allowed mime types are: {list(FileValidator.ALLOWED_MIME_TYPES)}", None, None

        # 3. Read size and check limits
        try:
            file_stream.seek(0, 2)
            file_size = file_stream.tell()
            file_stream.seek(0)
        except Exception as e:
            return False, f"Failed to check file size: {str(e)}", None, None

        if file_size > max_size_bytes:
            limit_mb = max_size_bytes / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            return False, f"File size exceeds limits. Limit: {limit_mb:.2f}MB, Actual: {actual_mb:.2f}MB", None, None

        if file_size == 0:
            return False, "File is empty (0 bytes).", None, None

        # 4. Open and decode using Pillow to verify corruption and resolution
        try:
            img = Image.open(file_stream)
            img.verify()  # Fast check for structural integrity
            
            # Re-open for size info since verify() might close/invalidate file
            file_stream.seek(0)
            img = Image.open(file_stream)
            width, height = img.size
            
            # Reset seek position for next readers
            file_stream.seek(0)
        except Exception as e:
            return False, f"File is corrupted or not a readable image: {str(e)}", None, None

        # 5. Check resolution boundaries
        if width < min_resolution[0] or height < min_resolution[1]:
            return False, f"Image resolution too low ({width}x{height}). Minimum required: {min_resolution[0]}x{min_resolution[1]}.", width, height

        if width > max_resolution[0] or height > max_resolution[1]:
            return False, f"Image resolution too high ({width}x{height}). Maximum allowed: {max_resolution[0]}x{max_resolution[1]}.", width, height

        return True, None, width, height


file_validator = FileValidator()
