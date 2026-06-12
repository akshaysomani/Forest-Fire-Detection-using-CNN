# System Monitoring Guide

This guide explains how to monitor the Forest Fire Detection application using the built-in system telemetry services.

---

## 1. System Telemetry Aggregates

The monitoring system pulls live resource levels from the host operating system:

1. **CPU Usage**: Retrieves total system CPU load percentage.
2. **RAM Memory**: Pulls total, used, and free RAM values (bytes) along with the percentage of memory currently locked by processes.
3. **Disk Storage**: Measures total space, free space, and percentage usage of the storage volumes.
4. **Active Session Logs**: Counts logged-in users with active (non-expired) sessions.

---

## 2. Health Protocols

The system executes active checking for critical services:

### 2.1 Database Pings
The `/health` endpoint checks database health by executing a quick query:
```python
res = await db.execute(text("SELECT 1"))
```
If the database goes offline or is locked by transactional write constraints, the check logs a critical error to the console and reports `unhealthy` status.

### 2.2 Storage Capacity Safe Boundaries
A drive space checks ensures disk storage usage is under **95%**. If the drive usage crosses this limit, the storage state is flagged as degraded, warning operators before CNN uploads fail due to out-of-disk exceptions.

---

## 3. Alerts & Logging Integration

If any system health check fails, the application records a critical error event in the console:

```json
{"timestamp": "2026-06-12T17:00:00.000Z", "level": "CRITICAL", "message": "Database health check failed: connection refused", "logger": "health_service"}
```

These logs are structured in JSON format, allowing easy ingestion by container orchestration platforms (like Kubernetes) and alert management tools (like Prometheus/Alertmanager) to broadcast notifications (PagerDuty, email, Slack) to site reliability engineers.
