import os
from app.services.storage_service import storage_service


class ArchiveManager:
    async def archive_file(self, file_path: str) -> str:
        """
        Simulate moving a file to a cold storage tier (e.g., Glacier/Archive).
        Copies the file content to an 'archive/' prefix and deletes the original.
        """
        if file_path.startswith("archive/"):
            return file_path

        try:
            content = await storage_service.read_file(file_path)
            archive_path = f"archive/{file_path}"
            await storage_service.save_file(content, archive_path)
            await storage_service.delete_file(file_path)
            return archive_path
        except Exception as e:
            # If read fails, file might already be archived or missing
            return file_path

    async def restore_file(self, archive_path: str) -> str:
        """
        Simulate restoring a file from a cold storage tier to the active tier.
        Removes the 'archive/' prefix.
        """
        if not archive_path.startswith("archive/"):
            return archive_path

        try:
            content = await storage_service.read_file(archive_path)
            original_path = archive_path.replace("archive/", "", 1)
            await storage_service.save_file(content, original_path)
            await storage_service.delete_file(archive_path)
            return original_path
        except Exception:
            return archive_path


archive_manager = ArchiveManager()
