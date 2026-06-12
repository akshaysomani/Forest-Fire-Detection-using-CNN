# Dashboard & System Monitoring Security Review

This review audits the security configuration, authorization boundaries, and risk vectors for the Dashboard & System Monitoring Module.

---

## 1. Authorization & Route Guards (RBAC)

All dashboard endpoints utilize FastAPI's dependency injection to enforce identity verification and granular permission checks prior to executing service logic:

- **Identity Validation**: Authenticated requests must carry a valid JWT access token passed via the `Authorization: Bearer <token>` header. Token structure and validity are checked by [deps.py:get_current_active_user](file:///c:/Users/OM%20TRIVEDI/Desktop/Forest-Fire-Detection-using-CNN/backend/app/api/deps.py#L43-L49).
- **Permission Enforcement**: Every route is guarded using a dedicated `PermissionChecker` dependency:
  - `/overview` & `/statistics`: requires `view_reports` permission.
  - `/recent-activity`: requires `access_audit_logs` permission (restricted to Super Admin).
  - `/system-summary`: requires `manage_platform_settings` permission (restricted to Super Admin).
  - `/user-summary`: requires `manage_users` permission (restricted to Super Admin).

---

## 2. Information Exposure Safeguards

### 2.1 User Metrics Isolation
- **Risk**: Exposing total user counts, active sessions, and growth curves to non-administrative users.
- **Remediation**: The `dashboard_service.py` intercepts requests from `Forest Officer` and other lower-privileged roles. When an officer calls the overview/statistics endpoints, database aggregates for `total_users` and `active_users` are hardcoded to `0` or filtered out.

### 2.2 Security Audit Omission
- **Risk**: Normal users reading IP addresses, user agents, or details of other users' security events.
- **Remediation**: The `/recent-activity` audit log endpoint requires the high-level administrative permission `access_audit_logs`. Lower roles requesting this endpoint receive a **403 Forbidden** response.

### 2.3 Hardware Detail Leakage
- **Risk**: Revealing disk paths, hostnames, or specific server details in system telemetry.
- **Remediation**: 
  - Telemetry endpoints are strictly limited to `Super Admin`.
  - Storage capacities are returned as generic integers (bytes) and percentage levels, avoiding the disclosure of underlying partition paths, mount names, or folder structures.

---

## 3. Telemetry Resource Leak Protection

To prevent Denial of Service (DoS) attacks on telemetry endpoints (e.g. hitting CPU/memory checks repeatedly to spike CPU), the following layers are implemented:

- **Caching Layer**: Responses for overview and statistics are cached for **30 seconds** in an async-safe, thread-safe memory manager. Under rapid concurrent request loops, database aggregate queries are executed at most twice per minute.
- **Rate Limiting**: Enforced globally by the `RateLimitMiddleware` (configured for 100 requests/minute per IP address).
