### Step 4: Dashboard, Metrics & Analytics Engine

The Analytics Engine drives views using historical and aggregate ML telemetry:

#### 1. Classification Verification Accuracy
Calculates how well the CNN model identifies fires compared to human verification (is_verified_fire):
$$\text{Accuracy} = \frac{\text{True Positives (TP)} + \text{True Negatives (TN)}}{\text{True Positives} + \text{True Negatives} + \text{False Positives} + \text{False Negatives}}$$
*Note: If no verifications are logged yet, the system returns a pre-deployment validation metric of `0.945` (94.5%) as a fallback.*

#### 2. Trend Bucket Interpolation
When graphing a 30-day window, missing dates with no uploads are filled in with `0` counts by `TrendAnalyzer` to ensure continuous frontend line charts:
```
Raw:        [(2026-06-10, 5), (2026-06-12, 3)]
Interpolated:     [(2026-06-10, 5), (2026-06-11, 0), (2026-06-12, 3)]
```

#### 3. TTL Caching Optimization
To prevent heavy DB aggregations, dashboard summaries are cached in-memory with a **30-second TTL** using an `asyncio.Lock` safe wrapper.

#### 4. API Endpoints Reference
All endpoints require a header: `Authorization: Bearer <JWT>`
- **`GET /api/v1/dashboard/overview`**: High-level counts. Non-admins only see their own uploads.
- **`GET /api/v1/dashboard/statistics`**: Extended aggregates (averages, confidence, CNN model distribution).
- **`GET /api/v1/dashboard/recent-activity`**: Paginated audit log records (Super Admin only).
- **`GET /api/v1/dashboard/system-summary`**: System metrics telemetry (Super Admin only).
- **`GET /api/v1/dashboard/user-summary`**: User count and growth distributions (Super Admin only).

---



### Step 12: Dataset Management API Reference

All API calls must contain the authentication header:
`Authorization: Bearer <JWT_ACCESS_TOKEN>`

#### Create Dataset
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

#### List Datasets (Paginated)
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

#### Upload Image
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

#### ZIP Dataset Upload (Async Background Job)
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

#### Create Version Snapshot
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

#### Rollback Dataset Version
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

#### Bulk Assign Labels
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

---



### Step 16: Image Storage API Reference

All endpoints require the HTTP Header: `Authorization: Bearer <JWT_ACCESS_TOKEN>`

| HTTP Method | Path | Description | Access Level |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/images/upload` | Upload a single image file | Forest Officer, Admin |
| `POST` | `/api/v1/images/bulk-upload` | Upload multiple image files concurrently | Forest Officer, Admin |
| `POST` | `/api/v1/images/upload-zip` | Upload a ZIP archive containing images | Forest Officer, Admin |
| `GET` | `/api/v1/images` | List registered images (paginated) | Viewer, Officer, Admin |
| `GET` | `/api/v1/images/search` | Advanced search with multi-parameter filter | Viewer, Officer, Admin |
| `GET` | `/api/v1/images/statistics` | Retrieve image database statistics | Viewer, Officer, Admin |
| `GET` | `/api/v1/images/{id}/stream` | Stream/Retrieve the binary image payload | Viewer, Officer, Admin |
| `GET` | `/api/v1/images/{id}/thumbnail` | Retrieve the WebP thumbnail representation | Viewer, Officer, Admin |
| `DELETE` | `/api/v1/images/{id}` | Soft delete a registered image | Super Admin |

#### Advanced Search Filter Query Parameters
- `source` (e.g. `drone`, `cctv`)
- `status` (e.g. `active`, `archived`)
- `min_width` / `max_width`, `min_height` / `max_height`
- `min_size` / `max_size` (bytes)
- `camera_make` / `camera_model`
- `min_lat` / `max_lat`, `min_lon` / `max_lon` (GPS coordinates)
- `skip`, `limit` (paging)

---



### Step 26: Training REST APIs & RBAC Controls

Endpoints require a secure `Authorization: Bearer <token>` header:

| Method | Path | Description | Access Level |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/training/start` | Start training in the background | Super Admin / Platform Mgr |
| `POST` | `/api/v1/training/stop/{run_id}` | Gracefully stop an active run | Super Admin / Platform Mgr |
| `POST` | `/api/v1/training/resume` | Resume run from the latest checkpoint | Super Admin / Platform Mgr |
| `GET` | `/api/v1/training/status/{run_id}` | Query current run status and metrics | Viewer and above |
| `GET` | `/api/v1/training/runs` | List training runs history (paginated) | Viewer and above |
| `GET` | `/api/v1/training/metrics/{run_id}` | Get loss/accuracy history for graphing | Viewer and above |
| `GET` | `/api/v1/training/checkpoints/{run_id}` | List checkpoints generated by a run | Viewer and above |

---



### Analytics API Reference





### Analytics API Reference

This document maps all REST API endpoints registered under the `/api/v1/analytics` router.

---

#### 1. Retrieve KPIs

*   **URL:** `GET /api/v1/analytics/kpis`
*   **Headers:** `Authorization: Bearer <JWT_ACCESS_TOKEN>`
*   **Query Parameters:**
    *   `bypass_cache` (bool, default=false): Force real-time query recalculation.
*   **Success Response (200 OK):**
    ```json
    {
      "fire_detection_count": 45,
      "detection_accuracy": 0.9556,
      "incident_resolution_time_min": 14.2,
      "alert_response_time_min": 1.5,
      "active_incidents": 3,
      "user_activity_count": 124,
      "dataset_growth_bytes": 10737418240,
      "model_performance_score": 0.982
    }
    ```

---

#### 2. Query KPI Trends

*   **URL:** `GET /api/v1/analytics/trends`
*   **Query Parameters:**
    *   `kpi_name` (string, required): e.g. `"fire_detection_count"`
    *   `days` (integer, default=30): Number of rolling historical days.
*   **Success Response (200 OK):**
    ```json
    {
      "kpi_name": "fire_detection_count",
      "trends": [
        {"date_bucket": "2026-06-12", "value": 3.0},
        {"date_bucket": "2026-06-13", "value": 5.0}
      ]
    }
    ```

---

#### 3. Generate Report

*   **URL:** `POST /api/v1/analytics/reports/generate`
*   **Request Body (JSON):**
    ```json
    {
      "report_type": "fire_detections",
      "format": "PDF",
      "parameters": {
        "start_date": "2026-06-01T00:00:00Z",
        "confidence": 0.90
      }
    }
    ```
*   **Success Response (200 OK):**
    ```json
    {
      "id": "e458ff62-23c2-482a-a924-a212e32a4e21",
      "report_definition_id": null,
      "report_type": "fire_detections",
      "executed_by": "a11d2ee2-349c-4ee2-b2ff-0f2c418241b1",
      "status": "completed",
      "format": "PDF",
      "parameters": {
        "start_date": "2026-06-01T00:00:00Z",
        "confidence": 0.90
      },
      "file_path": "reports/report_e458ff62-23c2-482a-a924-a212e32a4e21.pdf",
      "error_message": null,
      "execution_time_ms": 140,
      "created_at": "2026-06-13T15:00:00Z"
    }
    ```

---

#### 4. Download Export File

*   **URL:** `GET /api/v1/analytics/export`
*   **Query Parameters:**
    *   `execution_id` (UUID, required)
*   **Response:** Binary Stream.
    *   Sets headers:
        *   `Content-Type: application/pdf` (or `text/csv`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`)
        *   `Content-Disposition: attachment; filename=report_{uuid}.pdf`

---

#### 5. Executive Dashboard

*   **URL:** `GET /api/v1/analytics/executive-dashboard`
*   **Success Response (200 OK):**
    ```json
    {
      "kpis": {
        "fire_detection_count": 45,
        "detection_accuracy": 0.9556,
        "incident_resolution_time_min": 14.2,
        "alert_response_time_min": 1.5,
        "active_incidents": 3,
        "user_activity_count": 124,
        "dataset_growth_bytes": 10737418240,
        "model_performance_score": 0.982
      },
      "regional_risk_index": {
        "Pacific Northwest Region": 75.2,
        "Southeast Forestry Division": 45.1
      },
      "fire_hazard_level": "Medium",
      "active_responders_ratio": 0.354
    }
    ```

---





### Model API Reference





### Model Registry REST API Reference

This reference documents the API endpoints exposed under the `/api/v1/models` route prefix.

---

#### 1. Summary table of endpoints

| HTTP Method | Route Path | Required Permission | Description |
| :--- | :--- | :--- | :--- |
| **POST** | `/api/v1/models` | `manage_platform_settings` | Register a new model definition family. |
| **GET** | `/api/v1/models` | `view_reports` | List registered model families (paginated). |
| **GET** | `/api/v1/models/{id}` | `view_reports` | Retrieve a model family summary. |
| **POST** | `/api/v1/models/versions` | `manage_platform_settings` | Register a new version linked to a training run. |
| **GET** | `/api/v1/models/versions` | `view_reports` | List versions or compare two versions. |
| **GET** | `/api/v1/models/versions/{id}` | `view_reports` | Retrieve detailed model version configurations. |
| **POST** | `/api/v1/models/approve/request`| `manage_platform_settings` | Request model promotion to a target state. |
| **POST** | `/api/v1/models/approve` | `manage_platform_settings` | Submit review sign-off (approved or rejected). |
| **POST** | `/api/v1/models/deploy` | `manage_platform_settings` | Deploy version to environment & hot-swap weights. |
| **POST** | `/api/v1/models/rollback` | `manage_platform_settings` | Rollback environment to previous active deployment. |
| **GET** | `/api/v1/models/history` | `view_reports` | Retrieve chronological transition lifecycle log. |
| **GET** | `/api/v1/models/artifacts` | `view_reports` | List registered artifacts for a model version. |
| **GET** | `/api/v1/models/observability/metrics`| `view_reports` | Get system registry health metrics. |

---

#### 2. Key Payload & Response Structures

##### A. Register Model Version
*   **Endpoint:** `POST /api/v1/models/versions?increment_type=patch`
*   **Payload (`ModelVersionCreateRequest`):**
    ```json
    {
      "model_id": "84b472e4-3b26-4386-ab1d-f34c9907eb17",
      "training_run_id": "f75a7a90-9d0d-4d4d-800e-3efbe475088b",
      "checkpoint_id": "714ec24a-b51d-415f-9af1-2f5bcd9698ff",
      "description": "Retrained baseline CNN",
      "release_notes": "Trained for 10 epochs on smoke partition."
    }
    ```
*   **Response (`ModelVersionResponse` - HTTP 201):**
    ```json
    {
      "id": "645c8143-ee7a-4954-b21c-cc25ee8a4dff",
      "model_id": "84b472e4-3b26-4386-ab1d-f34c9907eb17",
      "version": "1.0.0",
      "training_run_id": "f75a7a90-9d0d-4d4d-800e-3efbe475088b",
      "checkpoint_id": "714ec24a-b51d-415f-9af1-2f5bcd9698ff",
      "status": "Draft",
      "created_by": "2d0e00b4-5a89-4ef7-ace5-a4323589c636",
      "description": "Retrained baseline CNN",
      "release_notes": "Trained for 10 epochs on smoke partition.",
      "metrics": {
        "val_loss": 0.15,
        "val_accuracy": 0.92,
        "accuracy": 0.92,
        "loss": 0.15,
        "epoch": 10
      },
      "hyperparameters": {
        "learning_rate": 0.001
      },
      "created_at": "2026-06-13T10:02:37",
      "updated_at": "2026-06-13T10:02:37"
    }
    ```

##### B. Deploy Model Version
*   **Endpoint:** `POST /api/v1/models/deploy`
*   **Payload (`ModelDeploymentRequest`):**
    ```json
    {
      "model_version_id": "645c8143-ee7a-4954-b21c-cc25ee8a4dff",
      "environment": "production"
    }
    ```
*   **Response (`ModelDeploymentResponse` - HTTP 200):**
    ```json
    {
      "id": "a3250b90-fa15-4fc9-af7d-c5578a217497",
      "model_version_id": "645c8143-ee7a-4954-b21c-cc25ee8a4dff",
      "environment": "production",
      "status": "active",
      "deployed_by": "2d0e00b4-5a89-4ef7-ace5-a4323589c636",
      "deployed_at": "2026-06-13T10:05:00",
      "undeployed_at": null,
      "metrics": null
    }
    ```

##### C. Compare Model Versions
*   **Endpoint:** `GET /api/v1/models/versions?version_a=645c8143-ee7a-4954-b21c-cc25ee8a4dff&version_b=714ec24a-b51d-415f-9af1-2f5bcd9698ff`
*   **Response (`ModelVersionCompareResponse` - HTTP 200):**
    ```json
    {
      "version_a": {
        "id": "645c8143-ee7a-4954-b21c-cc25ee8a4dff",
        "version": "1.0.0",
        "metrics": { "accuracy": 0.81 }
      },
      "version_b": {
        "id": "714ec24a-b51d-415f-9af1-2f5bcd9698ff",
        "version": "1.1.0",
        "metrics": { "accuracy": 0.87 }
      },
      "metrics_diff": {
        "accuracy": {
          "old": 0.81,
          "new": 0.87,
          "difference": 0.06
        }
      },
      "hyperparameters_diff": {
        "learning_rate": {
          "changed": true,
          "old": 0.001,
          "new": 0.002
        }
      }
    }
    ```

---



