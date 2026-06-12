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
        string token_hash UNIQUE
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