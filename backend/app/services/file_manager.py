import hashlib
import os
import re
import tempfile
import shutil
from typing import BinaryIO


class FileManager:
    @staticmethod
    def calculate_md5(data: bytes) -> str:
        """Calculate MD5 hash of raw bytes."""
        hasher = hashlib.md5()
        hasher.update(data)
        return hasher.hexdigest()

    @staticmethod
    def calculate_md5_stream(stream: BinaryIO) -> str:
        """Calculate MD5 hash of a binary stream, reading in chunks to prevent memory overhead."""
        hasher = hashlib.md5()
        # Ensure we are at the start of the stream
        try:
            stream.seek(0)
        except Exception:
            pass

        while chunk := stream.read(8192):
            hasher.update(chunk)

        try:
            stream.seek(0)
        except Exception:
            pass
        return hasher.hexdigest()

    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Return lowercased file extension, e.g. '.jpg'."""
        _, ext = os.path.splitext(filename)
        return ext.lower()

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal or invalid characters."""
        # Keep only word characters, dots, dashes, and underscores
        name = os.path.basename(filename)
        name = re.sub(r"[^\w\.\-\s]", "", name)
        # Replace spaces with underscores
        return name.replace(" ", "_")

    @staticmethod
    def create_temp_dir() -> str:
        """Create a secure temporary directory inside the system temp dir."""
        return tempfile.mkdtemp()

    @staticmethod
    def remove_dir(dir_path: str) -> None:
        """Remove a directory recursively if it exists."""
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            shutil.rmtree(dir_path, ignore_errors=True)


file_manager = FileManager()
