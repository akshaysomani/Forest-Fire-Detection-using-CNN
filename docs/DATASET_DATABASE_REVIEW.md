# Database Schema Review (DATASET_DATABASE_REVIEW.md)

This review details the database tables, relations, fields, index designs, and data integrity policies for the Dataset Management Module.

---

## 1. Schema Diagram & Relationships

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
        string name UNIQUE
        string description
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }

    DATASET_LABELS {
        uuid id PK
        string name UNIQUE
        string description
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }

    DATASETS {
        uuid id PK
        uuid category_id FK
        uuid user_id FK
        string name UNIQUE
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

---

## 2. Table Definitions & Security Standards

- **UUID Primary Keys**: All tables use `uuid.UUID` primary keys mapped via SQLAlchemy's `Uuid` column, preventing database enumeration attacks.
- **Soft Deletes**: Tables implement a `deleted_at` nullable timestamp column. Standard queries will exclude records where `deleted_at is not None` to prevent data loss.
- **Audit Trails**: Every modification triggers updating the `updated_at` field automatically (`onupdate=func.now()`). Clear auditing is tracked under the separate `dataset_audit_logs` table.
- **Foreign Key Integrity**:
  - `dataset_id` columns use `ondelete="CASCADE"` or `ondelete="SET NULL"` appropriately to avoid orphaned entries.
  - Strict foreign keys are enforced at compile time.

---

## 3. Database Index Optimizations

To handle large dataset listings and duplicate detection:
1. **`dataset_files(dataset_id, md5_hash)`**: Speeds up deduplication checks when uploading files to a dataset.
2. **`dataset_versions(dataset_id, version_str)`**: Ensures unique versions per dataset and accelerates queries for version history.
3. **`dataset_files(label_id)`**: Used to quickly aggregate category distributions.
4. **`dataset_audit_logs(dataset_id, created_at)`**: Optimizes fetching audit trails for dashboards.
