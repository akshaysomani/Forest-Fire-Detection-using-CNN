# Dataset Management Guide (DATASET_MANAGEMENT.md)

Welcome to the Forest Fire Detection Dataset Management Module. This module is designed to help ML engineers build, organize, validate, and version image datasets for training CNN models.

---

## 1. System Overview & Architecture

The module utilizes a clean Separation of Concerns (SoC) design:

```
                  [ FastAPI Endpoints ]
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
     [Upload Service]             [Version Service]
     - Single / Bulk uploads      - Create Snapshots
     - ZIP extractor worker       - Rollback manager
             │                           │
             └─────────────┬─────────────┘
                           ▼
                 [Validator Pipeline]
                 - Format & size check
                 - Image header decode
                 - MD5 deduplication
                           │
                           ▼
                  [Storage Service]
                  - Local filesystem
                  - S3 / GCS / Azure
```

---

## 2. Upload and Extraction Pipeline

1. **ZIP Upload**: Client calls `POST /api/v1/datasets/zip-upload` with a ZIP archive.
2. **Background Task**: The router creates an upload history record (status="pending") and hands extraction off to `DatasetProcessor` running in the background.
3. **Subfolder Classification**: Files inside folders like `fire/` are assigned the label `Fire` automatically, while those inside `non_fire/` are labeled `Non-Fire`.
4. **Active State Registry**: Active files are written to `datasets/{dataset_id}/raw/` and registered in the database as unversioned files.

---

## 3. Data Validation Pipeline

Every image passes through three validation layers before it is accepted:
1. **Format Validation**: Checks extension (`.jpg`, `.jpeg`, `.png`, `.webp`) and MIME types.
2. **Resolution & Size Validation**: Checks resolution boundaries (min 128x128, max 8192x8192) and limits sizes to 10MB.
3. **Structural Validation (Pillow check)**: Opens image headers and verifies no bitmap corruptions exist.
4. **MD5 Deduplication**: Checks MD5 hash against existing records in this dataset to prevent database contamination.

---

## 4. Versioning & Snapshots Strategy

- **Immutability**: Creating a version compiles all active files into a read-only ZIP file saved under `snapshots/{dataset_id}/{version}.zip`.
- **Database Mapping**: In the database, the files are assigned a `version_id` link. Any future upload modifications will only create new files (which remain unversioned until the next snapshot is created).
- **ML Rollbacks**: Rollbacks fetch previous version snapshots, clear current active files, and re-extract the snapshots back into the active workspace.
