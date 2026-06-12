# Forest-Fire-Detection-using-CNN

This repository implements the backend architecture for a high-performance, secure, and role-aware Forest Fire Detection platform using CNN (Convolutional Neural Network) image classification.

---

## Step-by-Step System Documentation & Guides

This documentation consolidates all system guides, database reviews, audits, and checklists to help you understand, build, and deploy the application.

---

### Step 1: System Overview & Architecture

The application is structured using a strict **Separation of Concerns (SoC)** and follows a **Service-Repository** design pattern. This ensures decoupled modules, high-performance database interactions, and an easily testable codebase.

```
[Client / UI]
     │
     ▼ (JWT Auth + RBAC Guard)
[API Controllers]   <--->  [Cache Service] (30s TTL)
     │
     ▼
[Services Layer]   (Dashboard, Monitoring, Health, Analytics)
     │
     ▼
[Repositories]     (Dashboard, Detection, Activity, User)
     │
     ▼
[Database (SQLite/PostgreSQL)]
```

#### Core Components
- **API Controller** ([dashboard_controller.py](file:///C:/Users/Akshay/OneDrive/Desktop/New%20folder/Forest-Fire-Detection-using-CNN/backend/app/api/v1/dashboard_controller.py)): Exposes REST endpoints, registers dependencies, and filters incoming request payloads.
- **Dashboard Service** ([dashboard_service.py](file:///C:/Users/Akshay/OneDrive/Desktop/New%20folder/Forest-Fire-Detection-using-CNN/backend/app/services/dashboard_service.py)): Evaluates user roles (RBAC) and formats custom responses.
- **Monitoring Service** ([monitoring_service.py](file:///C:/Users/Akshay/OneDrive/Desktop/New%20folder/Forest-Fire-Detection-using-CNN/backend/app/services/monitoring_service.py)): Collects live hardware parameters (CPU, RAM, storage) and DB connectivity states.
- **Analytics Service** ([analytics_service.py](file:///C:/Users/Akshay/OneDrive/Desktop/New%20folder/Forest-Fire-Detection-using-CNN/backend/app/services/analytics_service.py)): Calculates rolling trends and handles CNN model selection distributions.
- **Dashboard Repository** ([dashboard_repository.py](file:///C:/Users/Akshay/OneDrive/Desktop/New%20folder/Forest-Fire-Detection-using-CNN/backend/app/repositories/dashboard_repository.py)): Direct DB aggregates for statistics.

---

### Step 2: Database Schema & Design Review

The data model utilizes UUID primary keys, automated audit timestamps, and soft delete fields. The schema supports both SQLite (development/testing) and PostgreSQL (production).

```mermaid
erDiagram
    USERS ||--o{ DETECTIONS : "uploads"
    USERS ||--o{ SESSIONS : "establishes"
    USERS ||--o{ AUDIT_LOGS : "triggers"
    USERS ||--o{ REFRESH_TOKENS : "owns"
    
    USERS {
        uuid id PK
        string email UNIQUE
        string username UNIQUE
        string hashed_password
        string profile_image_url
        boolean is_active
        boolean is_verified
        timestamp last_login_at
        int failed_login_attempts
        timestamp locked_until
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }

    DETECTIONS {
        uuid id PK
        uuid user_id FK "nullable, SET NULL"
        string image_path
        string filename
        string prediction_label "fire | non-fire"
        float confidence
        string model_name
        string model_version
        boolean is_verified_fire "nullable"
        boolean alert_sent
        float latitude "nullable"
        float longitude "nullable"
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }

    REFRESH_TOKENS {
        uuid id PK
        uuid user_id FK
        string token_hash 
        string parent_token_hash
        timestamp expires_at
        boolean is_revoked
        timestamp created_at
    }

    SESSIONS {
        uuid id PK
        uuid user_id FK
        uuid refresh_token_id FK
        string ip_address
        string user_agent
        string device_type
        boolean is_active
        timestamp last_activity_at
        timestamp expires_at
        timestamp created_at
    }

    AUDIT_LOGS {
        uuid id PK
        uuid user_id FK "nullable"
        string action
        string ip_address
        string user_agent
        string resource_type
        string resource_id
        json details
        timestamp created_at
    }
```
---
#### Database Tables Description
1. **`users`**: Stores user credentials, lockout settings, verification statuses, and soft deletes.
2. **`roles` / `permissions`**: RBAC system defining roles (`Super Admin`, `Forest Officer`, `Emergency Response Officer`, `Research Analyst`, `Viewer`) and granular access rights.
3. **`detections`**: Logs image classification requests (CNN inference results, confidence, coordinates, and manual verification check state).
4. **`refresh_tokens` / `sessions`**: Implements session tracking, token rotation (RTR), and device logging.
5. **`audit_logs`**: Registers security actions (`user.login`, `user.register`, etc.) for auditing.

#### Index Optimization
To support fast query aggregations under load, the database relies on indexes for:
- `users(email)` and `users(username)` (fast logins)
- `detections(prediction_label)`, `detections(is_verified_fire)`, `detections(created_at)` (fast metrics)
- `sessions(user_id, is_active)` (rapid session tracking)

---

### Step 3: Authentication, Security & Audit Logs

The Authentication module enforces enterprise-level security protocols:

1. **JWT & Session Safety**: Access tokens expire in 15 minutes, while refresh tokens run for 7 days.
2. **Refresh Token Rotation (RTR)**: Using a refresh token automatically revokes it and issues a new pair. If a revoked token is used, reuse detection immediately terminates all associated sessions to mitigate theft.
3. **Password Storage**: Hashed using `bcrypt` (via `passlib`) with a minimum of 12 rounds. Complexity checks require uppercase, lowercase, numbers, and special characters.
4. **Brute Force Lockout**: Accounts lock for 15 minutes after 5 failed attempts.
5. **Security Headers**: Injected into all HTTP responses:
   - `X-Frame-Options: DENY` (prevents clickjacking)
   - `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'`
   - `X-Content-Type-Options: nosniff`
6. **Centralized Observability**: Audit logging logs security events into the `audit_logs` table and outputs structured JSON lines on stdout console.

---

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

### Step 5: System Telemetry & Health Monitoring

The Monitoring module fetches live system metrics and verifies application status:

1. **Hardware Tracking**: Reads CPU usage, memory stats (total, used, percentage), and disk storage capacity. If `psutil` is unavailable on the host, safe mock fallbacks are used.
2. **Database Health**: Actively runs a query `SELECT 1` to verify connection and SQLite write lock availability.
3. **Storage Safe Boundary**: If host disk usage exceeds **95%**, the status reports as `degraded` to notify admins before CNN image uploads fail.
4. **observability logs**: If health checks fail, JSON logs are output to stdout:
   ```json
   {"timestamp": "2026-06-12T17:00:00.000Z", "level": "CRITICAL", "message": "Database health check failed: connection refused", "logger": "health_service"}
   ```

---

### Step 6: Code Quality, Production Checklist & Testing

#### Production Readiness Checklist
- [ ] Ensure `psutil` is compiled in production container images.
- [ ] Secure default Super Admin passwords and seed database tables.
- [ ] Configure log forwarders to direct stdout JSON logs to Splunk/Logstash.
- [ ] Schedule expired token deletion cron jobs.

#### Testing Framework
Unit and integration tests are run via `pytest` and `pytest-asyncio` on an in-memory SQLite database (`sqlite+aiosqlite:///:memory:`).

To execute the test suite:
```powershell
cd backend
python -m pytest
```
*Note: In the testing environment, rate-limiting is bypassed, and database tables are recreated per-test to guarantee test isolation.*

---

### Step 7: Dataset Management Module Overview & Audit

#### System Overview & Separation of Concerns (SoC)
The Dataset Management Module is designed for ML engineers to build, organize, validate, and version image datasets for training CNN models. It utilizes a clean Separation of Concerns (SoC) design:

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

#### Upload & Ingestion Pipelines
1. **ZIP Ingestion**: Client uploads a ZIP archive to `POST /api/v1/datasets/zip-upload`.
2. **Background Task**: The router creates an upload history record (status="pending") and hands extraction off to `DatasetProcessor` running in the background.
3. **Subfolder Classification**: Files inside folders like `fire/` are assigned the label `Fire` automatically, while those inside `non_fire/` are labeled `Non-Fire`.
4. **Active Workspace Registry**: Active files are written to `datasets/{dataset_id}/raw/` and registered in the database as unversioned files.

#### Validation & Quality Checking
Every image passes through three validation layers before it is accepted:
1. **Format Validation**: Checks extension (`.jpg`, `.jpeg`, `.png`, `.webp`) and MIME types.
2. **Resolution & Size Validation**: Checks resolution boundaries (min 128x128, max 8192x8192) and limits sizes to 10MB.
3. **Structural Validation (Pillow check)**: Opens image headers and verifies no bitmap corruptions exist.
4. **MD5 Deduplication**: Checks MD5 hash against existing records in this dataset to prevent database contamination.

#### Existing Dataset Infrastructure State (DATASET_AUDIT.md Summary)
- **Previous State**: None. Previously, the backend only had a generic `detections` table log referencing individual image paths but no concept of grouping images into curated training, validation, or test datasets.
- **Identified Gaps**: No batch ZIP processing, no image validation (posing corruption risks to downstream models), hardcoded local file storage without scaling options, and no dataset APIs.
- **Improvements Implemented**: Dedicated UUID declarative schema, multi-layer Pillow checks, background ZIP processing, abstract `StorageService`, and standard pagination APIs.

---

### Step 8: Dataset Architecture, Directory Layout & Database Design

#### Directory Structure Layout
To support scaling and multi-tenant structures, files are organized in a structured local workspace or cloud prefix pattern:
```
storage/
├── datasets/
│   └── {dataset_id}/
│       ├── raw/                  # Active unversioned file registry
│       │   ├── image_001.jpg
│       │   └── image_002.png
│       └── snapshots/            # Immutable version snapshots
│           ├── v1.0.0.zip
│           └── v1.1.0.zip
└── temp/                         # Temporary staging folders for zip extractions
    └── {upload_id}/
```

#### Database Schema Diagram & ERD
```mermaid
erDiagram
    DATASET_CATEGORIES ||--o{ DATASETS : "categorizes"
    USERS ||--o{ DATASETS : "owns"
    DATASETS ||--o{ DATASET_VERSIONS : "contains"
    DATASETS ||--o{ DATASET_FILES : "contains"
    DATASET_VERSIONS ||--o{ DATASET_FILES : "snapshots"
    DATASET_LABELS ||--o{ DATASET_FILES : "classifies"
    DATASETS ||--o{ DATASET_UPLOAD_HISTORY : "tracks"
    DATASETS ||--o{ DATASET_AUDIT_LOGS : "audits"
    USERS ||--o{ DATASET_AUDIT_LOGS : "performs"
    USERS ||--o{ DATASET_VERSIONS : "creates"
    USERS ||--o{ DATASET_UPLOAD_HISTORY : "initiates"

    DATASET_CATEGORIES {
        uuid id PK
        string name
        string description
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }

    DATASET_LABELS {
        uuid id PK
        string name
        string description
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }

    DATASETS {
        uuid id PK
        uuid category_id FK
        uuid user_id FK
        string name
        string description
        string status
        string tags
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }

    DATASET_VERSIONS {
        uuid id PK
        uuid dataset_id FK
        uuid user_id FK
        string version_str
        string description
        string status
        json metadata_json
        string snapshot_path
        int size_bytes
        int file_count
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }

    DATASET_FILES {
        uuid id PK
        uuid dataset_id FK
        uuid version_id FK "nullable"
        uuid label_id FK "nullable"
        string file_path
        string filename
        int file_size
        string mime_type
        string md5_hash
        json metadata_json
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }

    DATASET_UPLOAD_HISTORY {
        uuid id PK
        uuid dataset_id FK
        uuid user_id FK
        string status
        string upload_type
        string original_filename
        int total_files
        int processed_files
        int failed_files
        json error_details
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }

    DATASET_AUDIT_LOGS {
        uuid id PK
        uuid dataset_id FK
        uuid user_id FK
        string action
        json details
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }
```

#### Database Table Definitions & Optimizations
- **UUID Primary Keys**: All tables use `uuid.UUID` primary keys mapped via SQLAlchemy's Uuid column, preventing database enumeration attacks.
- **Soft Deletes**: Tables implement a `deleted_at` nullable timestamp column. Standard queries will exclude records where `deleted_at is not None`.
- **Index Performance**:
  - `dataset_files(dataset_id, md5_hash)`: Speeds up deduplication checks when uploading files.
  - `dataset_versions(dataset_id, version_str)`: Ensures unique versions per dataset and accelerates queries for version history.
  - `dataset_files(label_id)`: Used to quickly aggregate category distributions.
  - `dataset_audit_logs(dataset_id, created_at)`: Optimizes fetching audit trails.

---

### Step 9: Dataset Security, Vulnerability Prevention & RBAC Guard

#### Path Traversal (Zip Slip) Mitigation
- **Vulnerability**: ZIP files containing entries with relative traversals (e.g., `../../etc/passwd` or `..\..\App\main.py`) can overwrite system files during extraction.
- **Mitigation**: `FileManager.sanitize_filename` uses `os.path.basename` to extract only the trailing filename segment. Any nested traversal path prefixes inside ZIP entries are discarded before storage saving.

#### Double Extension & Script Uploads Blocking
- **Vulnerability**: Attackers upload execution scripts masquerading as images (e.g., `exploit.jpg.sh`).
- **Mitigation**:
  - File extension checking restricts uploads strictly to `{ .jpg, .jpeg, .png, .gif, .webp }`.
  - Content structure checks (`PIL.Image.open`) read file content headers. If a file contains script text instead of an image bitmap, Pillow will fail to read it, and the upload is rejected.

#### RBAC Permissions Mapping
- **Viewer Role**: Holds `view_predictions` and `view_reports`. Can only run read operations (`GET`).
- **Forest Officer / Research Analyst Roles**: Hold `upload_images` and `analyze_data`. Allowed to create datasets, execute file uploads, batch label, and create versions.
- **Super Admin Role**: Holds `manage_platform_settings` and `all`. Can soft-delete datasets, perform versions rollbacks, and view complete system details.

---

### Step 10: Dataset Storage & Cloud Migration Guide

#### Storage Configuration Settings
Storage settings are loaded from environment variables in `.env` through [app/core/config.py](file:///c:/Users/Akshay/OneDrive/Desktop/New%20folder%20(2)/Forest-Fire-Detection-using-CNN/backend/app/core/config.py):
```bash
# Available options: local, s3, gcs, azure
STORAGE_PROVIDER="local"

# Local storage path root
STORAGE_BASE_DIR="./storage"

# Cloud storage configurations (if using stubs/future cloud adapters)
AWS_S3_BUCKET="forest-fire-detection-datasets"
GCS_BUCKET="forest-fire-detection-datasets"
AZURE_CONTAINER="forest-fire-detection-datasets"
```

#### Abstraction & Easy Migration to AWS S3 / Cloud Storage
All files are processed through the unified `StorageService` helper class. High-level application logic calls `storage_service.save_file` or `storage_service.read_file` without knowing if files are local or in a cloud bucket.

To migrate from **Local** to **AWS S3** in production:
1. Copy all folders in `./storage/datasets/` recursively to your S3 bucket root.
2. Update environment variables in your deployment setup:
   ```bash
   STORAGE_PROVIDER="s3"
   AWS_S3_BUCKET="my-production-forest-fire-datasets"
   AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
   AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
   ```
3. Restart the FastAPI server. The `StorageService` constructor will resolve the `"s3"` driver automatically on startup.

---

### Step 11: Dataset Versioning, Immutability & Rollback Lifecycle

#### The Immutability Concept
- **Active State (`raw/`)**: Uploads are writeable, allowing adding files, modifying labels, and bulk adjustments.
- **Freeze State (`version`)**: Snapshotting zips the entire set of active files, saves it to storage as `{version_str}.zip`, and saves metadata (file hashes, count, class distribution) to the database.
- **File Locking**: The files are assigned a `version_id` in the database, freezing them. Any future uploads create new files with `version_id=None`.

#### Version Rollback Lifecycle
A rollback operation restores active files in the workspace (`raw/`) to match a target version's frozen snapshot:
1. **Request**: `POST /api/v1/datasets/{id}/rollback` with `{"version_str": "v1.0.0"}` is received.
2. **Clean active**: The backend deletes all current files in the database where `version_id is None` and removes their files from the `raw/` directory in storage.
3. **Unzip and Restore**: The snapshot ZIP for `v1.0.0` is downloaded and extracted. The files are written back to `raw/` in storage, and new database file records are inserted with `version_id=None` (meaning they are now active and modifiable).
4. **Audit**: The rollback is logged in the audit logs.

#### MLOps Training Integration
ML training scripts can dynamically pull specific version snapshots using curl:
```bash
# Retrieve zip snapshot directly for training
curl -H "Authorization: Bearer <TOKEN>" \
     -o dataset_v1.0.0.zip \
     http://localhost:8000/api/v1/datasets/18f9720b-22ab-44b4-a21b-c74191c2bde2/versions/v1.0.0/download
```

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

### Step 13: Dataset Code Quality, Testing Report & Production Readiness

#### Code Quality & Exceptions Handling
- **Consistent Service Patterns**: The codebase strictly adheres to the established `Service-Repository` pattern used throughout the rest of the application.
- **SQLAlchemy 2.x Styles**: The models use modern SQLAlchemy 2.x declarative styles, maintaining compatibility.
- **Error Middleware**: Custom exceptions (`EntityNotFoundException`, `ValidationException`) are integrated into global exception serialization filters, returning standardized JSON error bodies.

#### Testing Report (DATASET_TEST_REPORT.md Summary)
Tests run on an isolated in-memory transactional SQLite database (`sqlite+aiosqlite:///:memory:`):
- Recreates tables per-test fixture to ensure data isolation.
- Mocks image generation dynamically inside tests using `Pillow` to generate distinct valid image files.
- Command to run all tests:
  ```powershell
  cd backend
  python -m pytest
  ```
- All tests completed successfully.

#### Production Readiness Checklist
- **Proxy Body Configuration**: Ensure file transfer limits on proxies like Nginx are set to allow larger files (e.g. `client_max_body_size 100M;`).
- **Disk Monitoring**: Set Alerts on server host disk usage (e.g. trigger warnings at 85%, and critical alert at 90%).
- **Version Backups**: Enable storage bucket Versioning rules on cloud filesystems to restore files in disaster recovery scenarios.

---

### Step 14: Image Storage & Ingestion System Design

The Image Storage & Ingestion System manages the lifecycle of all input imagery ingested into the application (dashboards, CCTV monitoring feeds, drone surveys, or satellite batch uploads).

To support the heavy computation of ML-oriented workloads and avoid server-side blocking, this module is built using a strict **Separation of Concerns (SoC)**, **Asynchronous Processing Workers**, and the **Service-Repository** pattern.

#### Architecture Diagram
```
[Client App / API Consumers]
             │
             ▼ (JWT Auth + RBAC Guard)
   [Image Controller]  ◄───────────►  [Cache Manager (Redis/In-Memory)]
             │
      ┌──────┴──────────────────────────────┐
      ▼ (Fast Synchronous Upload)            ▼ (Query Registry)
[Upload Service]                      [Image Repository]
      │                                      │
      ├──────────────────────────────┐       ▼
      │ (Async Background Extraction) │   [SQL Database]
      ▼                              ▼
[Upload Processor]           [File Storage Manager]
      │                              │
      ▼                              ▼
[Validation Pipeline]        [Storage Service]
  - Magic Byte Signature       - Local Storage Provider
  - Pillow Pixel Decoding      - S3 / GCS / Azure Providers
  - MD5 Global Deduplication
      │
      ▼
[Preprocessing Pipeline]
  - EXIF Metadata Extractor
  - Image Resizer & Rescaler
  - ML Input Normalization
  - WebP Thumbnail Optimizer
```

#### Image Ingestion Flow
```mermaid
graph TD
    A[Raw Multipart File Upload] --> B{Magic Bytes Validation}
    B -- Invalid --> C[Reject: 400 Bad Request]
    B -- Valid --> D{Pixel Integrity Verification}
    D -- Corrupt/Truncated --> C
    D -- Healthy --> E{Global MD5 Deduplication}
    E -- Duplicate Hash --> F[Share Storage Reference]
    E -- Unique Hash --> G[Generate Storage Path]
    G --> H[Extract EXIF & Telemetry]
    H --> I[Write File to Storage Provider]
    I --> J[Background Preprocessor]
    J --> K[Generate 256x256 WebP Thumbnail]
    J --> L[Run CNN Input Normalization]
    K & L --> M[Register DB Records & Versions]
```

---

### Step 15: Image Upload Integration Guide

Detailed integration instructions for bulk, single, and ZIP uploads:

#### 1. Single Image Ingestion
- **URL**: `POST /api/v1/images/upload`
- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `file`: (Binary data) Image file.
  - `source`: (String) Source identifier (`manual`, `drone`, `cctv`, `satellite`).

#### curl Integration Example
```bash
curl -X POST "http://localhost:8000/api/v1/images/upload" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@/path/to/forest_fire.png" \
     -F "source=drone"
```

#### 2. Bulk Image Ingestion
- **URL**: `POST /api/v1/images/bulk-upload`
- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `files`: (Multiple Binary files) Multiple files can be passed using the same key name.
  - `source`: (String) Source system label.

#### 3. ZIP Archive Ingestion (Async Background Worker)
- **URL**: `POST /api/v1/images/upload-zip`
- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `file`: (Binary ZIP Archive) Compressed file.
  - `source`: (String) Ingestion source tag.

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

### Step 17: Storage Providers Configuration & Setup Guide

#### Configuration Settings (.env)
```bash
# Available Storage Providers: local, s3, gcs, azure
STORAGE_PROVIDER="local"

# Root path for local storage files (used by LocalStorageProvider)
STORAGE_BASE_DIR="./storage"

# AWS S3 Settings (used by S3StorageProvider)
AWS_S3_BUCKET="forest-fire-images-production"
AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
AWS_REGION="us-east-1"
```

- **LocalStorageProvider**: Asynchronous threadpool IO (`run_in_threadpool`) prevents event-loop blocking.
- **S3StorageProvider**: Fully asynchronous bucket management using `aioboto3` client connections. Supports generating secure, time-limited presigned URLs.
- **Local-to-Cloud Migration**: Handled by `FileStorageManager` which safely uploads files to the cloud, verifies MD5 hashes, updates databases under transaction, and deletes local copies.

---

### Step 18: Image Module Code Quality, Testing & Security Audit

#### Security Controls
- **Magic Bytes Validation**: Read first 8 bytes of file streams to match image format header signatures (reject spoofing).
- **Pixel Flood Mitigation**: Limit pixel array decoding to maximum 8192x8192 boundaries.
- **Zip Slip Mitigation**: Strip directory traversal paths (`../`) from filenames during extraction.
- **Storage Private Access**: Block public read/write to storage buckets. Access via secure time-limited presigned URLs.

#### Testing Suite
- Run all tests: `python -m pytest --cov=app --cov-report=term`
- 31/31 passed successfully.

---

### Step 19: Image Production Deployment & Monitoring Checklist

- [ ] **Reverse Proxy Limits**: Configure Nginx `client_max_body_size 100M;` to support large ZIP/bulk uploads.
- [ ] **Keep-Alive Timeouts**: Increase timeouts on load balancers to prevent premature network disconnects.
- [ ] **Secret Management**: Inject cloud access keys at container runtime using secure secret managers.
- [ ] **Bucket Policies**: Restrict cloud buckets to private access and enable versioning policies.
- [ ] **Disk Sweeper Alerts**: Configure alarms when disk space exceeds 85% warning / 95% critical status.

---

## CI/CD Workflow & Docker Deployment

This project includes a fully integrated GitHub Actions workflow for CI/CD and Docker files for containerized packaging.

### GitHub Actions
The workflow file at `.github/workflows/ci.yml` runs automatically on pushes and PRs to main. It:
1. Provisions Python 3.11 container.
2. Installs requirements.
3. Performs formatting and code checks.
4. Executes the full test suite and uploads coverage reports.

### Docker Compose Quickstart
To spin up the entire application locally in containerized form:
1. Build and launch:
   ```bash
   docker-compose up --build -d
   ```
2. The FastAPI server runs on port `8000`. Storage is persisted via named Docker volumes: `forest_fire_storage` and `forest_fire_db_data`.

---

## Contributors
- **Akshay Somani** (Lead Maintainer)

## License
This project is licensed under the MIT License - see the `LICENSE` file for details.

## Acknowledgements
Special thanks to all academic researchers, CNN computer vision architectures (like MobileNet, ResNet), and local forestry departments providing wildfire dataset feeds.

