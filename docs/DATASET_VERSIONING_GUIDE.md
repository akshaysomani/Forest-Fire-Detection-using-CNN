# Dataset Versioning Guide (DATASET_VERSIONING_GUIDE.md)

This guide walks through using the Dataset Versioning System to capture immutable snapshots for model training reproducibility.

---

## 1. The Immutability Concept

In deep learning, model comparison requires training on identical data subsets. If a dataset is continuously updated with new images, reproducing a past model state is impossible.

Our versioning system fixes this:
- **Active State (`raw/`)**: Uploads are writeable, allowing adding files, modifying labels, and bulk adjustments.
- **Freeze State (`version`)**: Snapshotting zips the entire set of active files, saves it to storage as `{version_str}.zip`, and saves metadata (file hashes, count, class distribution) to the database.
- **File Locking**: The files are assigned a `version_id` in the database, freezing them. Any future uploads create new files with `version_id=None`.

---

## 2. Version Snapshot metadata.json Structure

Every version snapshot ZIP contains a `metadata.json` describing the data state:

```json
{
  "dataset_id": "18f9720b-22ab-44b4-a21b-c74191c2bde2",
  "version": "v1.0.0",
  "created_at": "2026-06-12T17:15:00Z",
  "created_by": "admin",
  "file_count": 150,
  "class_distribution": {
    "fire": 90,
    "non_fire": 60
  },
  "files": [
    {
      "id": "76af5d3b-34bc-45ef-a1cd-b23456789def",
      "filename": "fire_001.jpg",
      "md5_hash": "c4ca4238a0b923820dcc509a6f75849b",
      "file_size": 245100,
      "label": "Fire",
      "width": 1024,
      "height": 768
    }
  ]
}
```

---

## 3. Version Rollback Lifecycle

A rollback operation restores active files in the workspace (`raw/`) to match a target version's frozen snapshot:
1. **Request**: `POST /api/v1/datasets/{id}/rollback` with `{"version_str": "v1.0.0"}` is received.
2. **Clean active**: The backend deletes all current files in the database where `version_id is None` and removes their files from the `raw/` directory in storage.
3. **Unzip and Restore**: The snapshot ZIP for `v1.0.0` is downloaded and extracted. The files are written back to `raw/` in storage, and new database file records are inserted with `version_id=None` (meaning they are now active and modifiable).
4. **Audit**: The rollback is logged in the audit logs.

---

## 4. MLOps Training Integration

ML training scripts can dynamically pull specific version snapshots using curl:

```bash
# Retrieve zip snapshot directly for training
curl -H "Authorization: Bearer <TOKEN>" \
     -o dataset_v1.0.0.zip \
     http://localhost:8000/api/v1/datasets/18f9720b-22ab-44b4-a21b-c74191c2bde2/versions/v1.0.0/download
```

This guarantees that training runs are fully reproducible, fulfilling MLOps standards.
