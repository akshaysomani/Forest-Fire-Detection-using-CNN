# Dashboard & System Monitoring Module Audit

This audit reviews the current backend implementation of the Forest Fire Detection system, focusing on the infrastructure and logic available for constructing dashboard visualizations, monitoring services, and operational logs.

---

## 1. Existing Infrastructure Analysis

### 1.1 Existing Dashboard & Statistics Endpoints
- **Status**: **Absent**
- **Findings**: The only active router registered under the API Version 1 endpoints is `app.api.v1.auth`. There are no routes, services, or repositories for dashboard views or analytics compilation.

### 1.2 Existing Monitoring Functionality
- **Status**: **Minimal**
- **Findings**: 
  - There is a static `/health` check route defined in [main.py](file:///c:/Users/OM%20TRIVEDI/Desktop/Forest-Fire-Detection-using-CNN/backend/app/main.py#L104-L107) which returns `{"status": "healthy", "service": "Forest Fire Detection API"}`.
  - This check is completely static and does not perform active checks (e.g. database ping, storage health check, memory check). If the database goes offline or the disk is full, the health check will still report `healthy`.

### 1.3 Database Query & Model Assessment
- **Status**: **Auth-only**
- **Findings**: 
  - Tables exist for `users`, `roles`, `permissions`, `sessions`, `refresh_tokens`, and `audit_logs`.
  - There are **no tables** to store CNN models, uploaded fire/non-fire images, confidence ratings, model classification logs, or validation metrics.
  - Generating image processed metrics, fire detection rates, or model usage statistics is impossible without creating an image prediction schema.

### 1.4 Logging & Audit Compliance
- **Status**: **Basic**
- **Findings**: 
  - The database has an `audit_logs` table (`AuditLog` model) which registers basic actions like `user.login`, `user.register`, and `profile.update`.
  - However, logging is performed ad-hoc inline inside `user_service.py` by constructing `AuditLog` records directly and inserting them. This violates the Single Responsibility Principle and is not centralized or extensible.
  - There is no file-based or console-based structured logging (e.g. JSON log outputs) for external observability collectors (like Filebeat or Prometheus).

### 1.5 Caching Review
- **Status**: **None**
- **Findings**:
  - No caching mechanisms exist in the backend. 
  - Loading the dashboard will require executing database aggregations (such as counting total uploads, checking active sessions, calculating accuracy metrics) on every request, which will cause excessive SQLite lock waits under high user concurrency.

---

## 2. Identified Gaps & Vulnerabilities

| Category | Issue Description | Risk | Priority |
| :--- | :--- | :--- | :--- |
| **Data Models** | Missing `Detection` / `ImageUpload` table. Cannot track ML statistics. | Critical | High |
| **Monitoring** | `/health` check is static; does not verify SQLite lockouts or drive space. | Medium | High |
| **Aesthetics / Performance** | No caching for complex metric aggregations. Slow dashboard response times. | High | Medium |
| **Observability** | No structured JSON console output; tracking application activity requires DB writes. | Medium | Medium |
| **RBAC Security** | General statistics endpoints are not guarded; any user could view admin security details. | High | High |
| **Error Handling** | No custom exceptions for data aggregation or system failures. | Low | Medium |

---

## 3. Prioritized Recommendations

1. **Schema Expansion (High)**: Add a `Detection` model to track model inference history. Register it so that migrations/startups build it automatically.
2. **Health Verification (High)**: Upgrade `/health` check to perform real-time DB pings and disk capacity validation.
3. **Role Filtering (High)**: Implement RBAC decorators on dashboard endpoints to return user-appropriate statistics.
4. **Caching Layer (Medium)**: Build a thread-safe, in-memory TTL caching engine to optimize API responses.
5. **Centralized Logging (Medium)**: Abstract activity tracking into a standalone Service and Repository pattern. Implement structured JSON console outputs.
