import io
import json
import os
import zipfile
import uuid
from typing import Dict, Any
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import EntityNotFoundException, ValidationException
from app.models.dataset import DatasetFile, DatasetAuditLog, DatasetLabel
from app.repositories.dataset_repository import (
    dataset_repository,
    dataset_version_repository,
    dataset_file_repository,
)
from app.repositories.label_repository import label_repository
from app.services.storage_service import storage_service
from app.services.file_manager import file_manager


class VersionManager:
    async def compare_versions(self, db: AsyncSession, dataset_id: uuid.UUID, v1_str: str, v2_str: str) -> Dict[str, Any]:
        """
        Compare two dataset versions by checking metadata file hashes:
        - Lists files unique to v1 (deleted in v2)
        - Lists files unique to v2 (added in v2)
        - Lists files in both with different hashes (modified)
        """
        ver1 = await dataset_version_repository.get_by_dataset_and_version(db, dataset_id, v1_str)
        ver2 = await dataset_version_repository.get_by_dataset_and_version(db, dataset_id, v2_str)

        if not ver1:
            raise EntityNotFoundException(f"Version '{v1_str}' not found.")
        if not ver2:
            raise EntityNotFoundException(f"Version '{v2_str}' not found.")

        files1 = {f["filename"]: f for f in ver1.metadata_json.get("files", [])}
        files2 = {f["filename"]: f for f in ver2.metadata_json.get("files", [])}

        added = []
        removed = []
        modified = []
        unchanged = []

        # Find added or modified
        for fname, f2 in files2.items():
            if fname not in files1:
                added.append(f2)
            else:
                f1 = files1[fname]
                if f1["md5_hash"] != f2["md5_hash"]:
                    modified.append({"from": f1, "to": f2})
                else:
                    unchanged.append(f2)

        # Find removed
        for fname, f1 in files1.items():
            if fname not in files2:
                removed.append(f1)

        return {
            "v1": v1_str,
            "v2": v2_str,
            "added_count": len(added),
            "removed_count": len(removed),
            "modified_count": len(modified),
            "unchanged_count": len(unchanged),
            "added": added,
            "removed": removed,
            "modified": modified,
        }

    async def rollback_to_version(
        self, db: AsyncSession, dataset_id: uuid.UUID, version_str: str, user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Rollback active dataset state to a specific version:
        1. Fetch version and download snapshot ZIP.
        2. Clean up (delete) active (unversioned) file records and files on disk.
        3. Extract the snapshot zip.
        4. Re-upload files to the raw/ folder in storage.
        5. Re-register files as active (unversioned) in the database using snapshot metadata.
        """
        dataset = await dataset_repository.get_by_id(db, dataset_id)
        if not dataset:
            raise EntityNotFoundException(f"Dataset with ID {dataset_id} not found.")

        # Find target version
        version = await dataset_version_repository.get_by_dataset_and_version(db, dataset_id, version_str)
        if not version:
            raise EntityNotFoundException(f"Version '{version_str}' not found for dataset.")

        # 1. Read zip from storage
        try:
            zip_bytes = await storage_service.read_file(version.snapshot_path)
        except Exception as e:
            raise ValidationException(f"Failed to read version snapshot archive: {str(e)}")

        # 2. Extract ZIP to temp workspace
        temp_dir = file_manager.create_temp_dir()
        try:
            zip_stream = io.BytesIO(zip_bytes)
            with zipfile.ZipFile(zip_stream) as zipf:
                zipf.extractall(temp_dir)

            # 3. Read metadata.json from extracted ZIP
            metadata_file_path = os.path.join(temp_dir, "metadata.json")
            if not os.path.exists(metadata_file_path):
                raise ValidationException("Corrupted snapshot: metadata.json is missing.")

            with open(metadata_file_path, "r") as f:
                meta = json.load(f)

            # 4. Delete all files associated with the dataset
            delete_query = delete(DatasetFile).where(DatasetFile.dataset_id == dataset_id)
            await db.execute(delete_query)

            # 5. Restore files to raw/ storage and database
            restored_count = 0
            label_cache = {}

            for f_meta in meta.get("files", []):
                # Resolve label
                label_obj = None
                label_name = f_meta.get("label")
                if label_name:
                    if label_name not in label_cache:
                        label_obj = await label_repository.get_by_name(db, label_name)
                        label_cache[label_name] = label_obj
                    else:
                        label_obj = label_cache[label_name]

                # Determine relative file path in ZIP
                label_folder = label_name.lower().replace(" ", "_") if label_name else "unlabeled"
                local_file_path = os.path.join(temp_dir, label_folder, f_meta["filename"])

                if not os.path.exists(local_file_path):
                    continue

                with open(local_file_path, "rb") as lf:
                    file_bytes = lf.read()

                # Save to storage raw path
                destination_path = f"datasets/{str(dataset_id)}/raw/{f_meta['filename']}"
                await storage_service.save_file(file_bytes, destination_path)

                # Insert DatasetFile record
                new_db_file = DatasetFile(
                    dataset_id=dataset_id,
                    version_id=None,  # Reset version so it is active
                    file_path=destination_path,
                    filename=f_meta["filename"],
                    file_size=f_meta["file_size"],
                    mime_type=None,  # Let it be default
                    md5_hash=f_meta["md5_hash"],
                    label_id=label_obj.id if label_obj else None,
                    metadata_json={"width": f_meta.get("width"), "height": f_meta.get("height"), "restored_from": version_str},
                )
                db.add(new_db_file)
                restored_count += 1

            # Log audit
            audit_log = DatasetAuditLog(
                dataset_id=dataset_id,
                user_id=user_id,
                action="dataset.rollback",
                details={"version_str": version_str, "version_id": str(version.id), "restored_files_count": restored_count},
            )
            db.add(audit_log)
            await db.flush()

        finally:
            # Cleanup temp directory
            file_manager.remove_dir(temp_dir)

        return {
            "status": "success",
            "message": f"Successfully rolled back dataset to version '{version_str}'.",
            "restored_files": restored_count,
        }


version_manager = VersionManager()
