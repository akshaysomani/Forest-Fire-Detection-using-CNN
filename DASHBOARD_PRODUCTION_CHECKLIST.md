# Production Readiness Checklist

This checklist defines the validation tasks required before deploying the Dashboard & System Monitoring Module to a production cluster.

---

## 1. Environment & Telemetry Configuration
- [ ] **Dependency Update**: Confirm that `psutil` is listed in `requirements.txt` and successfully built during container image compilation.
- [ ] **Cache Configuration**: Adjust the cache TTL values (`dashboard_service.py` default is 30 seconds) based on predicted traffic load and database replication lag.
- [ ] **Geospatial Logging**: Ensure uploads supply valid coordinate metrics (`latitude` and `longitude`) so the Emergency Response dashboard maps alerts accurately.

---

## 2. Infrastructure Health Checks
- [ ] **Database ping integration**: Configure Kubernetes startup/liveness probes to poll the `/health` endpoint.
- [ ] **Disk Space Alerts**: Ensure host disk space metrics are monitored and alert rules trigger warnings if capacity crosses 90% utilization (DB safe threshold).

---

## 3. Observability & Auditing
- [ ] **Audit log redirection**: Redirect console stdout stream logs (emitted by `activity_logger.py` in JSON format) to centralized log collectors (e.g. Splunk, Logstash).
- [ ] **Database Partitioning**: If prediction invocation counts exceed 1,000,000 rows, set up database partition partitions on the `detections` table (partitioned on `created_at` date buckets).

---

## 4. Security Enforcement
- [ ] **JWT Tokens Check**: Validate that access token expiration limits (`ACCESS_TOKEN_EXPIRE_MINUTES`) are set to a tight window (e.g., 15 minutes).
- [ ] **RBAC Restrictions**: Confirm that default Super Admin credentials are changed from the standard environment settings (`DEFAULT_ADMIN_PASSWORD`).
