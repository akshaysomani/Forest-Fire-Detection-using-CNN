import io
import os
import zipfile
import uuid
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal
from app.models.dataset import DatasetUploadHistory, DatasetFile, DatasetAuditLog, DatasetLabel
from app.repositories.dataset_repository import (
    dataset_upload_history_repository,
    dataset_file_repository,
)
from app.repositories.label_repository import label_repository
from app.services.dataset_validator import dataset_validator
from app.services.storage_service import storage_service
from app.services.file_manager import file_manager


class DatasetProcessor:
    async def process_zip_upload(
        self,
        history_id: uuid.UUID,
        dataset_id: uuid.UUID,
        zip_file_bytes: bytes,
        user_id: uuid.UUID
    ) -> None:
        """
        Background task to process ZIP archive upload:
        - Extracts ZIP contents
        - Validates format, resolution, integrity, and MD5 duplication
        - Auto-assigns labels based on subfolder structure (e.g. fire/ -> Fire, non_fire/ -> Non-Fire)
        - Writes files to storage and updates history tracking.
        """
        # Create a new standalone DB session to perform operations in the background
        async with SessionLocal() as db:
            history = await dataset_upload_history_repository.get_by_id(db, history_id)
            if not history:
                return

            history.status = "processing"
            db.add(history)
            await db.commit()

            # Cache labels for rapid lookup
            labels_list = await label_repository.get_multi(db, limit=100)
            labels_map = {l.name.lower().replace(" ", "_"): l for l in labels_list}

            temp_dir = file_manager.create_temp_dir()
            processed_count = 0
            failed_count = 0
            errors: Dict[str, str] = {}

            try:
                zip_stream = io.BytesIO(zip_file_bytes)
                with zipfile.ZipFile(zip_stream) as zipf:
                    # Filter out directory entries and non-images
                    namelist = [
                        name for name in zipf.namelist()
                        if not name.endswith("/") and not os.path.basename(name).startswith(".")
                    ]
                    
                    history.total_files = len(namelist)
                    db.add(history)
                    await db.commit()

                    for name in namelist:
                        filename = os.path.basename(name)
                        sanitized_name = file_manager.sanitize_filename(filename)

                        # Auto-label detection based on ZIP folder structure
                        parts = name.split("/")
                        assigned_label = None
                        if len(parts) > 1:
                            folder_name = parts[-2].lower().replace("-", "_")
                            # Map folder name to closest label
                            if "non_fire" in folder_name or "nonfire" in folder_name:
                                assigned_label = labels_map.get("non-fire") or labels_map.get("non_fire")
                            elif "controlled" in folder_name:
                                assigned_label = labels_map.get("controlled_burn")
                            elif "human" in folder_name:
                                assigned_label = labels_map.get("human_activity")
                            elif "smoke" in folder_name:
                                assigned_label = labels_map.get("smoke")
                            elif "fire" in folder_name:
                                assigned_label = labels_map.get("fire")
                            elif "unknown" in folder_name:
                                assigned_label = labels_map.get("unknown")

                        # Read image file stream from ZIP
                        with zipf.open(name) as file_entry:
                            file_bytes = file_entry.read()
                            entry_stream = io.BytesIO(file_bytes)

                            # Validate file
                            val_report = await dataset_validator.validate_and_hash_file(
                                db=db,
                                dataset_id=dataset_id,
                                file_stream=entry_stream,
                                filename=sanitized_name
                            )

                            if val_report["is_valid"]:
                                # Save to storage provider
                                storage_dest = f"datasets/{str(dataset_id)}/raw/{sanitized_name}"
                                await storage_service.save_file(file_bytes, storage_dest)

                                # Register in DB
                                new_file = DatasetFile(
                                    dataset_id=dataset_id,
                                    version_id=None,
                                    file_path=storage_dest,
                                    filename=sanitized_name,
                                    file_size=val_report["file_size"],
                                    mime_type=None,
                                    md5_hash=val_report["md5_hash"],
                                    label_id=assigned_label.id if assigned_label else None,
                                    metadata_json={
                                        "width": val_report["width"],
                                        "height": val_report["height"],
                                        "extracted_from": history.original_filename
                                    }
                                )
                                db.add(new_file)
                                processed_count += 1
                            else:
                                failed_count += 1
                                errors[name] = val_report["error"] or "Validation failed"

                        # Update progress periodically
                        if (processed_count + failed_count) % 5 == 0:
                            history.processed_files = processed_count
                            history.failed_files = failed_count
                            history.error_details = errors
                            db.add(history)
                            await db.commit()

                # Finalize status
                history.status = "completed" if failed_count == 0 else "completed"  # Still completed, but lists errors
                if failed_count == len(namelist) and len(namelist) > 0:
                    history.status = "failed"
                
                history.processed_files = processed_count
                history.failed_files = failed_count
                history.error_details = errors
                db.add(history)

                # Add Audit Log
                audit = DatasetAuditLog(
                    dataset_id=dataset_id,
                    user_id=user_id,
                    action="dataset.upload_zip",
                    details={
                        "history_id": str(history_id),
                        "total_files": len(namelist),
                        "processed": processed_count,
                        "failed": failed_count
                    }
                )
                db.add(audit)
                await db.commit()

            except Exception as e:
                history.status = "failed"
                history.error_details = {"error": f"Internal extraction error: {str(e)}"}
                db.add(history)
                await db.commit()

            finally:
                file_manager.remove_dir(temp_dir)


dataset_processor = DatasetProcessor()
