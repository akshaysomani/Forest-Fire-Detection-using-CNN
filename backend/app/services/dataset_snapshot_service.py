import io
import json
import os
import zipfile
import uuid
from datetime import datetime
from typing import Sequence, Tuple
from app.models.dataset import DatasetFile
from app.services.storage_service import storage_service
from app.services.file_manager import file_manager


class DatasetSnapshotService:
    async def create_version_snapshot(
        self,
        dataset_id: uuid.UUID,
        version_str: str,
        files: Sequence[DatasetFile],
        creator_username: str,
        description: str | None = None
    ) -> Tuple[str, int, int, dict]:
        """
        Bundle files into a ZIP archive and save to storage:
        - Creates a ZIP in a temporary directory
        - Adds each file under its classified category sub-folder (e.g. fire/img.jpg, non_fire/img.jpg)
        - Injects a dataset-wide metadata.json inside the ZIP
        - Uploads ZIP to storage_service
        - Returns (snapshot_storage_path, size_bytes, file_count, metadata_json)
        """
        temp_dir = file_manager.create_temp_dir()
        zip_filename = f"{version_str}.zip"
        zip_path = os.path.join(temp_dir, zip_filename)

        file_count = 0
        class_distribution = {}

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # 1. Archive each file
                metadata_files_list = []
                for db_file in files:
                    # Determine target folder within zip based on label
                    label_folder = "unlabeled"
                    if db_file.label:
                        label_folder = db_file.label.name.lower().replace(" ", "_")

                    # Class count distribution
                    class_distribution[label_folder] = class_distribution.get(label_folder, 0) + 1

                    # Read raw file bytes from storage
                    try:
                        file_bytes = await storage_service.read_file(db_file.file_path)
                    except Exception as e:
                        # Fallback/Log, continue with other files if one is missing,
                        # but for strict integrity we expect it to exist
                        continue

                    # Put file in zip e.g., fire/my_image.jpg
                    zip_entry_path = f"{label_folder}/{db_file.filename}"
                    zipf.writestr(zip_entry_path, file_bytes)
                    file_count += 1

                    metadata_files_list.append({
                        "id": str(db_file.id),
                        "filename": db_file.filename,
                        "md5_hash": db_file.md5_hash,
                        "file_size": db_file.file_size,
                        "label": db_file.label.name if db_file.label else None,
                        "width": db_file.metadata_json.get("width") if db_file.metadata_json else None,
                        "height": db_file.metadata_json.get("height") if db_file.metadata_json else None,
                    })

                # 2. Add metadata.json to zip
                meta_payload = {
                    "dataset_id": str(dataset_id),
                    "version": version_str,
                    "created_at": datetime.utcnow().isoformat(),
                    "created_by": creator_username,
                    "description": description or "",
                    "file_count": file_count,
                    "class_distribution": class_distribution,
                    "files": metadata_files_list
                }
                zipf.writestr("metadata.json", json.dumps(meta_payload, indent=2))

            # 3. Read ZIP file bytes
            with open(zip_path, "rb") as f:
                zip_bytes = f.read()

            size_bytes = len(zip_bytes)
            
            # 4. Upload to storage
            storage_dest = f"datasets/{str(dataset_id)}/snapshots/{zip_filename}"
            await storage_service.save_file(zip_bytes, storage_dest)

        finally:
            # Cleanup temp zip directory
            file_manager.remove_dir(temp_dir)

        return storage_dest, size_bytes, file_count, meta_payload


dataset_snapshot_service = DatasetSnapshotService()
