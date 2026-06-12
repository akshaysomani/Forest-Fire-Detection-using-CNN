# Dataset Management Audit (DATASET_AUDIT.md)

This audit evaluates the current state of dataset management in the Forest Fire Detection application backend and identifies critical areas requiring enterprise-grade enhancements.

---

## 1. Existing Dataset Infrastructure State

- **Dataset Storage Structure**: None. Currently, the backend only has a generic `detections` table log referencing individual image paths but no concept of grouping images into curated training, validation, or test datasets.
- **Upload Functionality**: No formal dataset upload functionality exists. Image paths in `detections` are treated as individual standalone inference entries.
- **File Management Logic**: Lacks abstraction. There is no helper module to manage files, calculate checksums, detect duplicates, or interact with external storage providers.
- **Metadata Handling**: No metadata schemas or database attributes are available to record dataset properties (size, version, author, class distributions).
- **Validation Mechanisms**: Image validation is completely absent. Corrupted uploads or non-image formats are not filtered, posing risks to downstream CNN models.
- **Storage Providers**: Hardcoded local file storage logic only, offering no path to scale to cloud systems (AWS S3, Azure Blob, Google Cloud Storage).
- **Dataset APIs**: None. No endpoints exist for dataset CRUD, batch operations, labeling, version control, or status tracking.

---

## 2. Identified Inefficiencies & Gaps

### A. Missing Workflows
- **Batch Processing**: No ability to upload bulk images or ZIP files representing structured ML datasets.
- **Versioning**: No capability to capture dataset snapshots for model training reproducibility.
- **Labeling Interface**: No mechanism to tag files as `Fire` or `Non-Fire`, or to extend classification to `Smoke`, `Controlled Burn`, etc.

### B. Storage Inefficiencies
- **Duplicate Files**: Re-uploading identical images results in duplicate files on disk, wasting storage and introducing validation/test set contamination.
- **Single Threaded Copying**: Large ZIP extractions or bulk uploads block the main async event loop due to synchronous disk operations.

### C. Data Integrity Issues
- **Unvalidated Files**: Corrupted images or scripts uploaded as images could cause runtime failures in deep learning training pipelines.
- **Referential Integrity**: Lack of database schemas linking files, versions, and categories.

### D. Security Vulnerabilities
- **Path Traversal**: ZIP file extraction can be exploited (Zip Slip vulnerability) to write files outside target storage directories.
- **Malicious Uploads**: Lack of mime-type validation allows uploading execution scripts or double-extension files (e.g., `image.png.sh`).
- **Access Control**: Viewers can theoretically access raw folders if paths are leaked, since no dataset authorization guard exists.

---

## 3. Prioritized Recommendations

1. **High Priority (Phase 4, 10, 6)**: Define database entities using UUIDs, establish abstract storage providers (Local vs. Cloud), and build image magic-bytes verification.
2. **Medium Priority (Phase 5, 8, 7)**: Implement async background ZIP extraction, immutability snapshots for version control, and multi-label tagging.
3. **Operational (Phase 9, 12)**: Provide paginated REST APIs with Swagger documentation and ensure 90%+ test coverage.
