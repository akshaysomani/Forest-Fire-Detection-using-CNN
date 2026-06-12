# Dashboard & System Monitoring Module

This module implements high-performance, secure, and role-aware dashboard statistics and active system telemetry monitoring endpoints.

---

## 1. System Architecture

The module utilizes a clean Separation of Concerns (SoC) design:

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
[Repositories]     (Dashboard, Detection, Activity)
     │
     ▼
[Database (SQLite/PostgreSQL)]
```

### 1.1 Core Components
- **API Controller** ([dashboard_controller.py](file:///c:/Users/OM%20TRIVEDI/Desktop/Forest-Fire-Detection-using-CNN/backend/app/api/v1/dashboard_controller.py)): Exposes REST endpoints, registers dependencies, and filters incoming request payloads.
- **Dashboard Service** ([dashboard_service.py](file:///c:/Users/OM%20TRIVEDI/Desktop/Forest-Fire-Detection-using-CNN/backend/app/services/dashboard_service.py)): Evaluates roles (RBAC) and formats customized payloads.
- **Monitoring Service** ([monitoring_service.py](file:///c:/Users/OM%20TRIVEDI/Desktop/Forest-Fire-Detection-using-CNN/backend/app/services/monitoring_service.py)): Collects live hardware parameters (CPU, RAM, storage) and DB connectivity states.
- **Analytics Service** ([analytics_service.py](file:///c:/Users/OM%20TRIVEDI/Desktop/Forest-Fire-Detection-using-CNN/backend/app/services/analytics_service.py)): Drives time-series rolling trends and model selection ratios.
- **Dashboard Repository** ([dashboard_repository.py](file:///c:/Users/OM%20TRIVEDI/Desktop/Forest-Fire-Detection-using-CNN/backend/app/repositories/dashboard_repository.py)): Executes aggregated SQL/ORM transactions.

---

## 2. Telemetry and Caching Optimization

1. **In-Memory TTL Caching**: Statistics are stored in [dashboard_cache_service.py](file:///c:/Users/OM%20TRIVEDI/Desktop/Forest-Fire-Detection-using-CNN/backend/app/services/dashboard_cache_service.py) with a default **30-second TTL**. This prevents redundant aggregate operations on concurrent page loads.
2. **Lazy Loading Strategy**: Telemetry, user metrics, and historical charts are split into different endpoints. The frontend can query simple overview numbers immediately on page load, and deferred-load charts or system health indicators in the background.
