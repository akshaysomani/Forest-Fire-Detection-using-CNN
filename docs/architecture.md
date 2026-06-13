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

