# Dataset Storage Guide (DATASET_STORAGE_GUIDE.md)

This guide walks through configuring, optimizing, and migrating dataset storage drivers.

---

## 1. Storage Configuration Settings

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

---

## 2. File Organization on Local Disk

When using `"local"`, the files are laid out on disk starting from `STORAGE_BASE_DIR`:

```
./storage/
└── datasets/
    └── {dataset_uuid}/
        ├── raw/                  # Modifiable active files
        │   ├── fire_001.jpg
        │   └── non_fire_002.png
        └── snapshots/            # Sealed version snapshots
            ├── v1.0.0.zip
            └── v1.1.0.zip
```

---

## 3. Storage Abstraction & Easy Migration

All files are processed through the unified [StorageService](file:///c:/Users/Akshay/OneDrive/Desktop/New%20folder%20(2)/Forest-Fire-Detection-using-CNN/backend/app/services/storage_service.py). High-level application logic calls `storage_service.save_file` or `storage_service.read_file` without knowing if files are local or in a cloud bucket.

To migrate from **Local** to **AWS S3** in production:
1. Copy all folders in `./storage/datasets/` recursively to your S3 bucket root.
2. Update environment variables in your deployment setup:
   ```bash
   STORAGE_PROVIDER="s3"
   AWS_S3_BUCKET="my-production-forest-fire-datasets"
   AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
   AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
   ```
3. Restart the FastAPI server. The `StorageService` constructor will resolve the `"s3"` driver automatically.

---

## 4. Secure File Access Rules

- **Access Guarding**: The storage base directory is located outside the web server's static routing root directory. Static files are not directly routable, preventing unauthenticated access.
- **Payload Streaming**: Images are served to client interfaces through authenticated API controller streams (using FastAPI's `FileResponse` or `StreamingResponse`), which verify roles and authentication tokens.
- **Read-Only version snapshots**: Published snapshots (`snapshots/`) are write-once; the backend does not allow mutating existing snapshots.
