# Dataset Production Checklist (DATASET_PRODUCTION_CHECKLIST.md)

Prepare this module for production deployment.

---

## 1. Storage Scaling & Cloud Migration

- [ ] Change `STORAGE_PROVIDER` from `"local"` to `"s3"`, `"gcs"`, or `"azure"` in environment variables.
- [ ] Set up access credentials in environment variables for your cloud service.
- [ ] Configure life cycle rules on your cloud storage bucket to archive old versions or temp files older than 7 days.

---

## 2. Upload Scalability & Memory Limits

- [ ] Set the proxy body size limit (e.g. `client_max_body_size 100M;` in Nginx config) to allow large ZIP uploads.
- [ ] Run background worker extraction in a separate container if upload volumes are high, preventing resource contention on API containers.

---

## 3. Database & System Monitoring

- [ ] Monitor CPU, RAM, and Disk space using Prometheus/Grafana (leveraging the `/api/v1/dashboard/system-summary` telemetry endpoint).
- [ ] Configure alerts on disk space usage: trigger a warning alert at **85%** disk capacity and a critical alert at **90%** disk capacity.
- [ ] Ensure stdout JSON logs from the audit system are forwarded to a central log collector (Splunk/Datadog).

---

## 4. Backup & Disaster Recovery

- [ ] Schedule nightly database backups (SQLite `app.db` snapshotting or database dump if using PostgreSQL).
- [ ] Ensure cloud storage buckets have **Versioning** enabled to allow recovery from accidental dataset deletions.
- [ ] Document the restoration workflow:
  1. Restore database state from DB backup.
  2. Restore raw image paths and snapshots from bucket versioning.
  3. Verify data linkage integrity by running the test suite.
