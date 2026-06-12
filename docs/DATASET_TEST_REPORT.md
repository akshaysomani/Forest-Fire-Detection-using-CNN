# Dataset Testing Report (DATASET_TEST_REPORT.md)

This report logs test scopes, mock setups, execution methods, and coverage parameters for the Dataset Management Module.

---

## 1. Test Suite Architecture

All dataset tests run on an isolated, transactional in-memory SQLite database (`sqlite+aiosqlite:///:memory:`) using the standard `pytest` and `pytest-asyncio` frameworks.
- **Fixture Isolation**: Tables are created and seeded with default roles and permissions before each test, and dropped afterward (`drop_all`), preventing data leaks between tests.
- **Transactional Rollback**: Database session queries are rolled back at the end of each test method block.
- **Dependency Overrides**: The application's `get_db` database connection dependency is intercepted to inject the active test session.

---

## 2. Test Cases and Coverage

The test suite [tests/test_dataset.py](file:///c:/Users/Akshay/OneDrive/Desktop/New%20folder%20(2)/Forest-Fire-Detection-using-CNN/backend/tests/test_dataset.py) covers:

| Test Case Name | Target Code component | Validation Criteria |
| :--- | :--- | :--- |
| `test_dataset_categories_and_labels_seeded` | `dataset_service.seed_categories_and_labels` | Checks that standard categories and labels are populated during database startup. |
| `test_dataset_lifecycle_and_rbac` | `dataset_service` & `dataset_controller` | Validates CRUD endpoints, and verifies that Viewers cannot create/delete datasets while Officers/Admins can. |
| `test_dataset_upload_and_validation` | `dataset_upload_service` & `file_validator` | Verifies image uploading, content format validation (rejects txt files), and duplicate checks (rejects same MD5 twice). |
| `test_dataset_versioning_and_rollback` | `dataset_version_service` & `version_manager` | Verifies freeze snapshots zip compilation, version metadata creation, and unzipping/restoration rollback. |
| `test_bulk_label_mapping` | `label_manager` & `dataset_controller` | Validates updating labels on lists of files. |

---

## 3. Mock Assets Setup

Images are generated dynamically inside tests using Python's `Pillow` library:
- Synthesizes 200x200 pixels PNG image data in memory (`io.BytesIO`).
- Generates unique file contents by varying fill colors (red, green, blue), producing different MD5 checksums dynamically.
- Eliminates the need for physical testing images inside the repository.
