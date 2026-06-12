# Dataset Security Review (DATASET_SECURITY_REVIEW.md)

This review documents security assessments, mitigations, and compliance rules built into the Dataset Management Module.

---

## 1. Upload Vulnerability Assessment

### A. Zip Slip (Path Traversal) Prevention
- **Vulnerability**: ZIP files containing entries with relative traversals (e.g., `../../etc/passwd` or `..\..\App\main.py`) can overwrite system files during extraction.
- **Mitigation**: `FileManager.sanitize_filename` uses `os.path.basename` to extract only the trailing filename segment. Any nested traversal path prefixes inside ZIP entries are discarded before storage saving.

### B. Double Extension and Script Uploads
- **Vulnerability**: Attackers upload execution scripts masquerading as images (e.g., `exploit.jpg.sh`).
- **Mitigation**: 
  - File extension checking restricts uploads strictly to `{ .jpg, .jpeg, .png, .gif, .webp }`.
  - Content structure checks (`PIL.Image.open`) read file content headers. If a file contains script text instead of an image bitmap, Pillow will fail to read it, and the upload is rejected.

---

## 2. Storage Security Audit

- **Directory Isolation**: Relative file paths saved in the database are appended to the configuration base path `STORAGE_BASE_DIR` using safe path operations, preventing directory escaping.
- **MD5 Content Addressing**: Uploaded files are hashed with MD5. In addition to detecting duplicates, hashing prevents file overwrite conflicts when separate users upload different files with the same name.
- **Read-Only Version Snapshots**: Once a version snapshot is compiled, it is saved under the read-only snapshots prefix. The rollback operation reads from this static archive without modifying the snapshot itself.

---

## 3. Access Control & Role-Based Security (RBAC)

FastAPI routes are protected using standard permissions:
- **Viewer Role**: Holds `view_predictions` and `view_reports`. Can only run read operations (`GET`).
- **Forest Officer / Research Analyst Roles**: Hold `upload_images` and `analyze_data`. Allowed to create datasets, execute file uploads, batch label, and create versions.
- **Super Admin Role**: Holds `manage_platform_settings` and `all`. Can soft-delete datasets, perform versions rollbacks, and view complete system details.

---

## 4. Data Leakage Review

- **Storage Location Protection**: The storage folders are placed outside the web server's static routing root. Images are retrieved only via signed endpoints or authenticated streaming API routes, preventing unauthenticated direct access.
- **JSON Serialization Limits**: Database model entities are mapped to strict Pydantic response models, preventing leaking internal keys or hashed credentials in API responses.
