# Phase 12: Inference Security Review

This report audits the authorization safeguards, network data policies, memory bounds, and threat mitigations implemented for the CNN Inference module.

---

## 1. Access Control Audit (RBAC Integration)

Endpoints mapped under the new `prediction_controller.py` strictly enforce the project's pre-existing Role-Based Access Control guards:

*   **Prediction Runs (`POST /predictions`, `POST /predictions/batch`):**
    *   Protected by `PermissionChecker("upload_images")`.
    *   Allows **Super Admin** and **Forest Officer** to initiate predictions.
    *   Restricts unauthorized users (e.g. viewers or unauthenticated callers) with a `403 Forbidden` response.
*   **Prediction Read & Telemetry (`GET /predictions`, `GET /predictions/{id}`, `GET /predictions/statistics`):**
    *   Protected by `PermissionChecker("view_predictions")`.
    *   Allows all registered users (**Forest Officer**, **Emergency Response Officer**, **Research Analyst**, and **Viewer**) to inspect history records.

---

## 2. API Security & Input Hardening

*   **File Upload Validation:**
    *   The `InputValidator` checks input image streams against a strict file size limit of **15MB**. This mitigates Denial of Service (DoS) attacks attempting to cause Out-of-Memory (OOM) crashes by submitting huge files.
    *   Strict MIME type checking ensures that only valid images (`image/jpeg`, `image/png`, `image/webp`) are accepted. This prevents Remote Code Execution (RCE) via malicious script uploads.
    *   Image processing uses Pillow's `Image.open().verify()` to check file integrity and catch corrupted buffers or formatting exploits before passing tensors to PyTorch.

---

## 3. Database Security & Parameterization

*   **SQL Injection Prevention:**
    *   All DB queries implemented in `PredictionRepository` use SQLAlchemy's 2.0 ORM expressions (`select`, `and_`, `func.count()`). This ensures that parameters are bound safely by the database driver, eliminating the risk of SQL injection.
*   **Audit Trail:**
    *   Inference triggers automatic system activity logs via `activity_logger.log_activity` to track who predicted what, when, and with which model version.

---

## 4. Threat Modeling Summary

| Threat Vector | Mitigation Strategy | Status |
| :--- | :--- | :--- |
| **Model Weight Poisoning** | Models can only be loaded from paths specified in the DB registry compiled from trusted training runs. | **Secured** |
| **Denial of Service (DoS)** | 15MB file size limit + global rate limiter middleware (100 requests/minute). | **Secured** |
| **Privilege Escalation** | Permission dependency guards require validated JWT sub tokens with specific active roles. | **Secured** |
| **Memory Exhaustion (RAM)** | Local LRU cache eviction restricts cached PyTorch model footprint to `max_cached_models=3`. | **Secured** |
