# Dataset Management API Reference (DATASET_API_REFERENCE.md)

All API calls must contain the authentication header:
`Authorization: Bearer <JWT_ACCESS_TOKEN>`

---

## 1. Endpoints List

### Create Dataset
- **Route**: `POST /api/v1/datasets`
- **Role Guard**: Forest Officer, Research Analyst, Super Admin
- **Payload**:
```json
{
  "name": "Forest Fires Summer 2026",
  "description": "Images collected from Uttarakhand forest zones during June 2026.",
  "category_id": "893c72b2-6019-4828-98e6-11b017b2b85e",
  "tags": "uttarakhand,fire,summer"
}
```
- **Response (201 Created)**:
```json
{
  "id": "18f9720b-22ab-44b4-a21b-c74191c2bde2",
  "name": "Forest Fires Summer 2026",
  "description": "Images collected from Uttarakhand forest zones during June 2026.",
  "category_id": "893c72b2-6019-4828-98e6-11b017b2b85e",
  "status": "active",
  "tags": "uttarakhand,fire,summer",
  "user_id": "3a7b6c8d-90ab-12cd-34ef-567890abcdef",
  "created_at": "2026-06-12T17:00:00Z",
  "updated_at": "2026-06-12T17:00:00Z"
}
```

### List Datasets (Paginated)
- **Route**: `GET /api/v1/datasets?skip=0&limit=10&search=Summer`
- **Role Guard**: Any active user
- **Response (200 OK)**:
```json
{
  "total": 1,
  "skip": 0,
  "limit": 10,
  "items": [
    {
      "id": "18f9720b-22ab-44b4-a21b-c74191c2bde2",
      "name": "Forest Fires Summer 2026",
      "category_id": "893c72b2-6019-4828-98e6-11b017b2b85e",
      "status": "active",
      "tags": "uttarakhand,fire,summer",
      "user_id": "3a7b6c8d-90ab-12cd-34ef-567890abcdef",
      "created_at": "2026-06-12T17:00:00Z",
      "updated_at": "2026-06-12T17:00:00Z"
    }
  ]
}
```

### Upload Image
- **Route**: `POST /api/v1/datasets/upload`
- **Format**: `multipart/form-data`
- **Parameters**:
  - `dataset_id` (Form Field UUID)
  - `label_id` (Form Field UUID, Optional)
  - `file` (Binary Image File)
- **Response (201 Created)**:
```json
{
  "id": "76af5d3b-34bc-45ef-a1cd-b23456789def",
  "dataset_id": "18f9720b-22ab-44b4-a21b-c74191c2bde2",
  "version_id": null,
  "file_path": "datasets/18f9720b-22ab-44b4-a21b-c74191c2bde2/raw/fire_001.jpg",
  "filename": "fire_001.jpg",
  "file_size": 245100,
  "mime_type": "image/jpeg",
  "md5_hash": "c4ca4238a0b923820dcc509a6f75849b",
  "label_id": "ccaa123b-45bc-67de-ef89-101112131415",
  "metadata_json": {
    "width": 1024,
    "height": 768
  },
  "created_at": "2026-06-12T17:05:00Z",
  "updated_at": "2026-06-12T17:05:00Z"
}
```

### ZIP Dataset Upload (Async Background Job)
- **Route**: `POST /api/v1/datasets/zip-upload`
- **Format**: `multipart/form-data`
- **Parameters**:
  - `dataset_id` (Form Field UUID)
  - `file` (Binary ZIP File)
- **Response (202 Accepted)**:
```json
{
  "id": "99bb123c-45de-67fg-89hi-jklmnopqrs12",
  "dataset_id": "18f9720b-22ab-44b4-a21b-c74191c2bde2",
  "user_id": "3a7b6c8d-90ab-12cd-34ef-567890abcdef",
  "status": "pending",
  "upload_type": "zip",
  "original_filename": "archive.zip",
  "total_files": 0,
  "processed_files": 0,
  "failed_files": 0,
  "error_details": null,
  "created_at": "2026-06-12T17:10:00Z",
  "updated_at": "2026-06-12T17:10:00Z"
}
```

### Create Version Snapshot
- **Route**: `POST /api/v1/datasets/{id}/versions`
- **Payload**:
```json
{
  "version_str": "v1.0.0",
  "description": "First baseline dataset snapshot containing 150 checked images."
}
```
- **Response (201 Created)**:
```json
{
  "id": "aabbccdd-eeff-0011-2233-445566778899",
  "dataset_id": "18f9720b-22ab-44b4-a21b-c74191c2bde2",
  "version_str": "v1.0.0",
  "description": "First baseline dataset snapshot containing 150 checked images.",
  "status": "active",
  "user_id": "3a7b6c8d-90ab-12cd-34ef-567890abcdef",
  "snapshot_path": "datasets/18f9720b-22ab-44b4-a21b-c74191c2bde2/snapshots/v1.0.0.zip",
  "size_bytes": 14210080,
  "file_count": 150,
  "created_at": "2026-06-12T17:15:00Z",
  "updated_at": "2026-06-12T17:15:00Z"
}
```

### Rollback Dataset Version
- **Route**: `POST /api/v1/datasets/{id}/rollback`
- **Payload**:
```json
{
  "version_str": "v1.0.0"
}
```
- **Response (200 OK)**:
```json
{
  "status": "success",
  "message": "Successfully rolled back dataset to version 'v1.0.0'.",
  "restored_files": 150
}
```

### Bulk Assign Labels
- **Route**: `POST /api/v1/datasets/{id}/labels`
- **Payload**:
```json
{
  "file_ids": [
    "76af5d3b-34bc-45ef-a1cd-b23456789def"
  ],
  "label_id": "ccaa123b-45bc-67de-ef89-101112131415"
}
```
- **Response (200 OK)**:
```json
{
  "status": "success",
  "updated_count": 1
}
```
