import io
import logging
from PIL import Image
from app.core.exceptions import ValidationException

logger = logging.getLogger("inference.input_validator")


class InputValidator:
    # Max file size: 15MB
    MAX_FILE_SIZE = 15 * 1024 * 1024
    
    # Supported image formats
    SUPPORTED_FORMATS = {"JPEG", "JPG", "PNG", "WEBP"}
    
    # Supported MIME types
    SUPPORTED_MIMES = {"image/jpeg", "image/png", "image/webp"}

    @staticmethod
    def validate_image_bytes(file_bytes: bytes, filename: str) -> None:
        """
        Validate image bytes for file size, format, MIME type, and data corruption.
        Raises ValidationException if invalid.
        """
        if not file_bytes:
            raise ValidationException("Empty image payload provided.")

        # 1. Size check
        if len(file_bytes) > InputValidator.MAX_FILE_SIZE:
            raise ValidationException(
                f"File size exceeds maximum allowed size of 15MB. Current size: {len(file_bytes) / (1024 * 1024):.2f}MB"
            )

        # 2. Parse check using Pillow
        try:
            img = Image.open(io.BytesIO(file_bytes))
            img.verify()  # Verifies integrity without decoding entire image data
        except Exception as e:
            logger.error(f"Pillow verification failed for image '{filename}': {e}")
            raise ValidationException(f"Corrupted or invalid image file: {str(e)}")

        # 3. Format validation
        try:
            # Need to reopen as verify() closes or invalidates the image pointer/stream
            img = Image.open(io.BytesIO(file_bytes))
            img_format = img.format.upper() if img.format else ""
            if img_format not in InputValidator.SUPPORTED_FORMATS:
                raise ValidationException(
                    f"Unsupported image format: {img_format}. Supported formats are: {list(InputValidator.SUPPORTED_FORMATS)}"
                )
        except Exception as e:
            if isinstance(e, ValidationException):
                raise e
            raise ValidationException(f"Failed to inspect image format: {str(e)}")


input_validator = InputValidator()
