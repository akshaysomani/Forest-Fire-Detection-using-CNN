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



### Analytics Security Review





### Analytics Security Review

This document reviews the security posture, authentication requirements, role-based authorization rules, and data protection practices within the Analytics & Reporting Platform module.

---

#### 1. Authentication & Security Architecture

All analytical endpoints are securely guarded under the main authentication middleware stack:
1.  **JWT Verification:** Clients must provide a valid JSON Web Token (JWT) in the `Authorization: Bearer <token>` header.
2.  **User Session Verification:** Active token identifiers are cross-referenced with live database records to prevent access from deactivated or deleted accounts.
3.  **Cross-Origin Isolation:** All analytical responses include standard security headers (`X-Frame-Options: DENY`, `Content-Security-Policy`) preventing clickjacking or token leakage.

---

#### 2. Role-Based Access Controls (RBAC) Mappings

Endpoints verify that the authenticated client holds specific permissions in the role mappings:

| Endpoint | Method | Required Permission | Allowed Roles |
| :--- | :--- | :--- | :--- |
| `/analytics/kpis` | GET | `view_reports` | Super Admin, Forest Officer, Responders, Analysts, Viewers |
| `/analytics/trends` | GET | `view_reports` | Super Admin, Forest Officer, Responders, Analysts, Viewers |
| `/analytics/reports` | GET | `view_reports` | Super Admin, Forest Officer, Responders, Analysts, Viewers |
| `/analytics/reports/definitions` | POST | `manage_platform_settings`| Super Admin only |
| `/analytics/reports/generate` | POST | `view_reports` | Super Admin, Forest Officer, Responders, Analysts, Viewers |
| `/analytics/reports/{id}` | GET | `view_reports` | Super Admin, Forest Officer, Responders, Analysts, Viewers |
| `/analytics/export` | GET | `view_reports` | Super Admin, Forest Officer, Responders, Analysts, Viewers |
| `/analytics/executive-dashboard` | GET | `view_reports` | Super Admin, Forest Officer, Responders, Analysts, Viewers |

---

#### 3. Data Protection & Export Protection

*   **Directory Traversal Guard:** Report filenames are generated dynamically using random UUIDs (e.g. `reports/report_{uuid}.pdf`). The storage layer cleans paths and denies relative directory traversals (such as `../` attacks).
*   **SQL Injection Prevention:** All reports, aggregations, and KPI queries are constructed using SQLAlchemy 2.0's type-safe `select()` and parameters mapping. No raw SQL strings are concatenated.
*   **Soft Delete Isolation:** The DB sessions automatically exclude soft-deleted rows using `.where(deleted_at.is_(None))` clauses across all analytical calculations, preventing deleted data from leaking into public spreadsheets.
*   **CSV Injection Mitigation:** Export utilities format values carefully to prevent Microsoft Excel formula injection attacks (e.g., cell values starting with `=`, `+`, `-`, or `@` are sanitized).

---





### Model Registry Security Review





### Model Registry Security & Access Control Review

This review assesses the security controls, access policies, validation gates, and auditable trails implemented for the Model Registry and Governance module.

---

#### 1. Role-Based Access Control (RBAC) Architecture

To prevent unauthorized model registrations, malicious weight tampering, and accidental rollbacks, a strict RBAC policy is enforced at the API controller layer:

| API Operation | Endpoint | Required Permission | Authorized Roles |
| :--- | :--- | :--- | :--- |
| **Register Family** | `POST /models` | `manage_platform_settings` | Super Admin, Platform Manager |
| **Register Version** | `POST /models/versions` | `manage_platform_settings` | Super Admin, Platform Manager |
| **Request Promotion** | `POST /models/approve/request` | `manage_platform_settings` | Super Admin, Platform Manager |
| **Review & Approve** | `POST /models/approve` | `manage_platform_settings` | Super Admin, Platform Manager |
| **Deploy Version** | `POST /models/deploy` | `manage_platform_settings` | Super Admin, Platform Manager |
| **Rollback Deployment** | `POST /models/rollback` | `manage_platform_settings` | Super Admin, Platform Manager |
| **List Models/Versions** | `GET /models` | `view_reports` | Forest Officer, Dispatcher, Viewers |
| **Compare Versions** | `GET /models/versions` | `view_reports` | Forest Officer, Dispatcher, Viewers |
| **Query History** | `GET /models/history` | `view_reports` | Forest Officer, Dispatcher, Viewers |
| **List Artifacts** | `GET /models/artifacts` | `view_reports` | Forest Officer, Dispatcher, Viewers |

*   **Authentication Guard:** All routes require a valid JWT access token passed via Authorization Bearer headers (validated by `get_current_active_user`).

---

#### 2. Artifact Storage & Integrity Security

Model checkpoints are stored as binary serialized Torch weights. Untrusted model loading poses severe security risks (e.g. arbitrary code execution via Python pickle in PyTorch). The following security measures are implemented:

1.  **File Integrity Hash Validation:**
    *   During registration, the system reads weights bytes in a stream and computes a **SHA256 checksum**.
    *   This checksum is recorded immutably in the `model_artifacts` table.
    *   When loading weights for live prediction, the checkpoint path is checked, and future modules can perform validation against the database-recorded hash to detect any off-band modifications of weights files on the disk/bucket.
2.  **Access Isolation:**
    *   Checkpoints are saved in subdirectories (`/storage/runs/`) where write permissions are restricted strictly to the system user executing the FastAPI backend process.
3.  **No Direct Uploads:**
    *   Model weights cannot be uploaded directly via open REST endpoints. The API only registers checkpoints produced natively by the system's training pipeline thread, guaranteeing lineage.

---

#### 3. Deployment Safety Gates

Deploying a model version to a staging or production environment triggers automated compliance logic:

1.  **Immutability Policy:**
    *   Once a model version is promoted beyond `Draft` state (e.g. `Validation`, `Approved`, `Staging`, `Production`), it becomes **immutable**. Any attempt to modify its description, reference run, metrics, or hyperparameters throws a `ValidationException`.
2.  **State-Machine Validation:**
    *   Direct promotion from `Draft` or `Validation` to `Production` is locked.
    *   A version must be promoted through valid transition paths and have an approved `ModelApproval` review record signed by an administrator to go live.
3.  **Automated Metrics Gate:**
    *   Promotion to `Approved` or higher is blocked if the version accuracy is below `80%` or if validation loss exceeds safe bounds.

---

#### 4. Auditing & Compliance Tracking

For accountability and government audit requirements, every administrative operation triggers duplicate records:

1.  **Audit Ledger:**
    *   The `model_audit_logs` table records the operator UUID, exact action (e.g., `register_model_version`, `submit_review`, `deploy_model`), client IP address, and transition payloads.
    *   Logs support soft deletes but are designed to be immutable once created.
2.  **Lifecycle History:**
    *   The `model_lifecycle_events` table acts as a time-series record of state changes, ensuring reviewers can trace who validation-tested, who approved, and who deployed a model.

---





### MLOps Security Review





### MLOps Platform Security Review

This document performs a comprehensive security audit and hardening review of the MLOps Automation and Deployment Orchestration Platform module.

#### 1. Secret Management & Cryptography
*   **Encrypted Configuration Data:** Dynamic environment configurations are scanned for key-value pairs matching secure vaults. Values prefixed with `vault::` are parsed and decrypted at runtime via simulated secure vault integrations (mock decryption reverses string payload as a placeholder for KMS integrations).
*   **Decryption Pipeline:** The `ConfigLoader.decrypt_dict_secrets` function recursively parses and decrypts dictionaries to prevent cleartext credentials from resting in memory.

#### 2. Role-Based Access Control (RBAC)
Endpoints are strictly validated using FastAPI dependency injection checks:
*   **Write Operations:** `POST /deployments`, `POST /deployments/promote`, and `POST /deployments/rollback` enforce the `manage_platform_settings` permission.
*   **Read Operations:** `GET /deployments`, `GET /deployments/history`, `GET /deployments/environments`, `GET /deployments/releases`, and `GET /deployments/observability/metrics` enforce the `view_reports` permission.

#### 3. Container & Infrastructure Hardening
*   **Docker Container Security:**
    *   **Non-Root Execution:** Container execution runs under user ID `10001` and group `10001` (`appuser:appgroup`), avoiding root access.
    *   **Secure Multi-Stage Build:** Builder stages compile requirements, keeping runner size minimized and preventing build tools (compilers, git, etc.) from existing in production runtimes.
*   **Kubernetes Manifest Safety:**
    *   `allowPrivilegeEscalation` is explicitly set to `false`.
    *   All default Linux kernel capabilities are dropped (`capabilities.drop: - ALL`).

---





### Module 14: Enterprise Security, Compliance & Governance Platform

This section details the design, auditing results, architecture, implementation guides, API endpoints, testing outcomes, and production readiness checks for the **Enterprise Security, Compliance & Governance Platform (Module 14)**.

---

#### 1. Security Audit Report (Phase 1)

##### 1.1 Vulnerabilities & Security Misconfigurations
During the initial scan of the application configuration and endpoints, the following items were analyzed:
- **Unprotected API Inputs**: Exploits like SQL Injection, Cross-Site Scripting (XSS), and Path Traversal could bypass routers if query parameters and body payloads were not sanitized or verified globally.
- **Secret Management Exposures**: Storing API keys, database credentials, and token secrets in plaintext environment variables or properties files increases the risk of code-leakage exposure.
- **Privilege Escalation Risks**: Lack of regular access certifications could result in "privilege creep" where user accounts maintain administrative roles long after their operational need has expired.
- **Compliance Gaps**: Lack of automated policy checks (GDPR / SOC2) and data retention runs meant the system was vulnerable to compliance audits.

##### 1.2 Prioritized Remediation Recommendations
1. **Global Request Filtering**: Deploy a global request interception middleware executing regex-based threat scans on path, headers, query parameters, and body inputs.
2. **Symmetric Secret Encryption**: Encrypt all third-party API keys and credentials at rest using derived key hashes and Fernet symmetric cryptography.
3. **Automated Identity Certifications**: Implement access review campaigns to force periodic manager review and revocation of role assignments.
4. **Policy Enforcement Engine**: Run programmatic SOC2 and GDPR compliance audits periodically.
5. **Standardized Security Logging**: Emit SIEM-compatible structured JSON audit records for all auth, administrative, and threat events.

---

#### 2. Security Architecture Review (Phase 2)

##### 2.1 Defense in Depth
The platform implements a multi-layered defense model:
- **Perimeter/Transport**: Secure headers block iframe-embedding, content type sniffing, and clickjacking attacks.
- **Middleware**: Intercepts requests to check IP blacklists, check rate limit counters, and scan payloads for SQLi/XSS/Traversal patterns.
- **Application Routing**: Enforces strict RBAC via route-guard dependencies (`PermissionChecker`).
- **Database/Storage**: Confidential columns (such as emails or coordinates) are encrypted at rest using `EncryptionManager` symmetric keys.

##### 2.2 Zero Trust & Least Privilege Access
- **No Implicit Trust**: All client connections are authenticated and authorized on every request. Even internal API calls carry explicit authorization header checks.
- **Least Privilege Roles**: System functions are mapped to discrete permissions (`upload_images`, `view_reports`, `manage_platform_settings`). Users are assigned specific roles representing only their operational duties (e.g. Forest Officer, Emergency Response Officer).
- **Default Deny**: Endpoints block access unless the client carries a valid JWT access token containing the required permission scopes.

---

#### 3. Identity & Access Governance Framework (Phases 3 & 9)

##### 3.1 Role Lifecycle & Permission Audits
The `IdentityGovernanceService` manages the role registry. Adding, deleting, or updating permissions associated with roles triggers security event logs. System admins run permission audits (`GET /security/audit`) to identify:
- **Orphaned Accounts**: Active accounts that haven't authenticated in over 90 days.
- **Excessive Privileges**: Standard users holding more than 5 distinct permissions.
- **Unverified Administrators**: Accounts holding elevated admin permissions that have not verified their email credentials.

##### 3.2 Access Certification Campaigns
Administrators launch periodic certification campaigns:
- **Campaign Creation**: Campaigns specify target roles (e.g. Forest Officer).
- **Reviewer Action**: Managers review role assignments and submit decisions (`CERTIFIED` or `REVOKED`).
- **Immediate Enforcement**: Rejections trigger immediate revocation of the role from the user in the database.

---

#### 4. Secret Management & Data Protection Manual (Phases 4, 5, & 9)

##### 4.1 Cryptographic Key Derivation & Encryption
- **Key Derivation**: The system derives key material url-safe representations using SHA-256 hashes of the master secret key.
- **Credential Storage**: Sensitive values like third-party GIS API tokens and storage keys are stored encrypted.
- **PII Masking**: Telemetry feeds, log outputs, and standard dashboard JSON payloads mask PII fields (e.g. `u***@forestfire.org`, `+123****789`, `**.****` coordinates) to prevent log leakage of sensitive user data.

##### 4.2 Automated Secret Rotation
- The `CredentialRotationService` handles rotating API keys and tokens.
- Each rotation generates a unique log entry (`SecretRotationLog`) and triggers a high-severity security event.

---

#### 5. API Security & Threat Mitigation Strategy (Phases 6, 10, & 9)

##### 5.1 Throttling & Blacklists
- **Rate Limiting**: Monitored per IP address. Exceeding 100 requests per minute triggers an auto-block response.
- **IP Blacklisting**: Threat events instantly blacklist IPs. Requests from blacklisted clients are rejected with `403 Forbidden` at the middleware layer.

##### 5.2 Exploit Prevention Patterns
The threat detection engine uses regular expressions to catch:
- **SQL Injection**: Matches expressions like `SELECT ... FROM`, `UNION SELECT`, `OR 1=1`, or command chain symbols (`--`, `/*`).
- **Cross-Site Scripting**: Blocks patterns containing `<script>`, `javascript:`, `onerror=`, or `onload=`.
- **Path Traversal**: Flags characters matching `../`, `..\`, `/etc/passwd`, or windows ini extensions.

---

#### 6. Security Event Management & Auditing (Phases 7 & 9)

##### 6.1 SIEM / SOC JSON Log Format
Standardized audit logging is structured for easy parsing by SOC/SIEM aggregators (Splunk, Elastic, Datadog):
```json
{
  "@timestamp": "2026-06-13T15:10:00Z",
  "event.category": "security",
  "event.type": "THREAT_BLOCKED",
  "log.level": "CRITICAL",
  "message": "Malicious request block: SQL_INJECTION_DETECTION (QUERY)",
  "user.id": null,
  "client.ip": "127.0.0.1",
  "user_agent.original": "Mozilla/5.0 ...",
  "security.details": {
    "path": "/api/v1/health",
    "query": "param=union select null",
    "threat": "SQL_INJECTION_DETECTION (QUERY)"
  }
}
```

##### 6.2 Incident Tracking Lifecycle
- **Escalation**: HIGH/CRITICAL events are logged in the database as open incidents.
- **Resolution**: Admins submit resolution summaries. If the threat is resolved, any associated IP block is automatically removed.

---

#### 7. Compliance Manager & Governance Dashboard (Phases 8 & 11)

##### 7.1 Programmatic Compliance Audits (Policy Engine)
- **SOC2 Audit Rules**: Checks that audit logging is active and that default administrative configurations are verified.
- **GDPR Audit Rules**: Ensures that data retention pruning cycles are running and that no raw PII leaks into log entries.

##### 7.2 Data Retention Pruning
- Prunes audit logs older than 180 days.
- Prunes security events older than 90 days.
- Prunes observability logs older than 30 days.

##### 7.3 Governance Dashboard
- **Executive Console**: Aggregates risk scores, policy compliance percentages, pending access reviews, active threat indicators, and rotation timestamps.

---

#### 8. Security APIs Reference (Phase 9)

All routes require a valid JWT token passed via the HTTP Header: `Authorization: Bearer <TOKEN>`

| HTTP Method | Path | Description | Required Permission |
|:---|:---|:---|:---|
| `GET` | `/api/v1/security/governance` | Governance metrics summary | `view_reports` |
| `GET` | `/api/v1/security/threats` | Active threat indicators and blocked IPs | `access_audit_logs` |
| `GET` | `/api/v1/security/compliance` | Get compliance scan status | `manage_platform_settings` |
| `POST` | `/api/v1/security/compliance/run/{policy_name}` | Run compliance policy validation scan | `manage_platform_settings` |
| `GET` | `/api/v1/security/audit` | Trigger and retrieve permission compliance audit | `access_audit_logs` |
| `GET` | `/api/v1/security/events` | Query security log events | `access_audit_logs` |
| `GET` | `/api/v1/security/access-reviews` | Fetch all access reviews campaigns | `manage_users` |
| `POST` | `/api/v1/security/access-reviews` | Create access review campaign | `manage_users` |
| `POST` | `/api/v1/security/access-reviews/{campaign_id}/decisions` | Submit campaign decision (CERTIFIED/REVOKED) | `manage_users` |
| `POST` | `/api/v1/security/rotate-secrets` | Trigger credentials rotation cycle | `manage_platform_settings` |

---

#### 9. Enterprise Security Review & Testing Report (Phases 12 & 13)

##### 9.1 Test Execution Summary
```
Platform: Windows 10 (Python 3.13.13)
Framework: pytest 8.4.2 + pytest-asyncio 1.2.0
Database: SQLite (in-memory)
Total Security Tests: 12
Passed: 12
Failed: 0
Duration: 7.84s
```

##### 9.2 Test Coverage Map

| Category | Tests | Status |
|:---|:---|:---|
| Cryptographic Manager | Encryption/Decryption round trip | ✅ Passed |
| Data Classification | PII mapping and masking | ✅ Passed |
| Threat Engine | SQLi, XSS, Path Traversal regex matching | ✅ Passed |
| API Throttling & Blocks | IP blacklisting and rate limits block | ✅ Passed |
| Identity Governance | Role creation, user assignment, and revocation | ✅ Passed |
| Access Certification | Campaign creation, decisions, and immediate role revocation | ✅ Passed |
| Secret Management | Seeding and credentials rotation | ✅ Passed |
| Data Retention | Pruning execution | ✅ Passed |
| Compliance Scans | SOC2 and GDPR audit runs | ✅ Passed |
| API Route Security | Auth requirements, Admin query, and Threat Block middleware | ✅ Passed |

---

#### 10. Security Code Review (Phase 15)

- **Cryptographic Key Handling**: Derived url-safe key material prevents runtime crashes during Fernet initialization.
- **Decoupled Business Logic**: Zero dependencies on existing core engines guarantee no breaking changes.
- **Standardized Type Safety**: Fully annotated async methods using Python 3.10+ types.

---

#### 11. Security Production Readiness Checklist (Phase 16)

- [x] All database models use UUID primary keys with soft delete support.
- [x] OWASP secure HTTP headers (CSP, HSTS, X-Frame-Options, nosniff) injected on every response.
- [x] Database-backed access review tracking with immediate revocation triggers.
- [x] Symmetric secret encryption with url-safe Fernet derived keys.
- [x] Request payload unquoting before threat evaluation to block obfuscated attacks.
- [x] Automated data retention rules pruning logs and database tables based on compliance windows.
- [x] Multi-layered auth and RBAC guards active on all administrative endpoints.
- [ ] Configure file forwarder to ship SIEM JSON log outputs (tagged with `[SECURITY_AUDIT]`) to central indexers (Elastic/Splunk).
- [ ] Store derived master cryptographic key in an HSM or secure key vault (AWS KMS, GCP KMS, HashiCorp Vault) rather than environment variables.
- [ ] Set up notifications (Webhooks/PagerDuty) for high-severity SecurityEvent entries.


---



