# Dashboard & System Monitoring API Reference

All dashboard endpoints are mounted under `/api/v1/dashboard`.

---

## 1. Authentication Headers
All endpoints require a valid JSON Web Token (JWT) passed in the HTTP header:
```http
Authorization: Bearer <your_access_token>
```

---

## 2. Endpoint Specifications

### 2.1 Get Overview
Returns high-level overview statistics. Non-administrators (like Forest Officers) will only see metrics matching their own uploads.
* **Route**: `GET /api/v1/dashboard/overview`
* **Response Code**: `200 OK`
* **Response Body Example (Super Admin)**:
  ```json
  {
    "total_users": 14,
    "active_users": 2,
    "total_uploaded_images": 328,
    "images_processed": 328,
    "fire_detections": 128,
    "non_fire_detections": 200,
    "detection_accuracy": 0.9654
  }
  ```

### 2.2 Get Statistics
Returns advanced aggregates including CNN model usage summaries.
* **Route**: `GET /api/v1/dashboard/statistics`
* **Response Code**: `200 OK`
* **Response Body Example**:
  ```json
  {
    "total_users": 14,
    "active_users": 2,
    "total_uploaded_images": 328,
    "images_processed": 328,
    "fire_detections": 128,
    "non_fire_detections": 200,
    "detection_accuracy": 0.9654,
    "model_usage_statistics": [
      {
        "model_name": "CNN_ResNet50_v1",
        "model_version": "1.0.0",
        "count": 228,
        "average_confidence": 0.9815
      },
      {
        "model_name": "CNN_MobileNet_v2",
        "model_version": "2.1.0",
        "count": 100,
        "average_confidence": 0.9412
      }
    ],
    "average_confidence": 0.9692
  }
  ```

### 2.3 Get Recent Activity
Returns a paginated list of security audit logs.
* **Route**: `GET /api/v1/dashboard/recent-activity`
* **Access**: **Super Admin only** (`access_audit_logs` permission)
* **Query Parameters**:
  - `skip` (default: 0): Offset counter.
  - `limit` (default: 25, max: 100): Limit counter.
* **Response Code**: `200 OK`
* **Response Body Example**:
  ```json
  {
    "activities": [
      {
        "id": "e9c0b11a-1d54-4a41-b4f0-8c2ea755bb1d",
        "user_id": "8c3ea755-1d54-4a41-b4f0-e9c0b11a1d54",
        "username": "admin",
        "action": "user.login",
        "resource_type": "user",
        "resource_id": "8c3ea755-1d54-4a41-b4f0-e9c0b11a1d54",
        "ip_address": "127.0.0.1",
        "details": {},
        "created_at": "2026-06-12T17:00:00Z"
      }
    ],
    "total_count": 142
  }
  ```

### 2.4 Get System Summary
Returns live system health and performance statistics.
* **Route**: `GET /api/v1/dashboard/system-summary`
* **Access**: **Super Admin only** (`manage_platform_settings` permission)
* **Response Code**: `200 OK`
* **Response Body Example**:
  ```json
  {
    "api_status": "healthy",
    "database_status": "healthy",
    "storage_usage": {
      "total_bytes": 107374182400,
      "used_bytes": 37580963840,
      "free_bytes": 69793218560,
      "percentage_used": 35.0
    },
    "cpu_usage_percent": 12.5,
    "memory_usage": {
      "total_bytes": 8589934592,
      "used_bytes": 3435973836,
      "free_bytes": 5153960756,
      "percentage_used": 40.0
    },
    "active_sessions": 2,
    "background_jobs_status": "healthy",
    "queue_status": "healthy"
  }
  ```

### 2.5 Get User Summary
Returns platform user metrics and registrations growth curves.
* **Route**: `GET /api/v1/dashboard/user-summary`
* **Access**: **Super Admin only** (`manage_users` permission)
* **Response Code**: `200 OK`
* **Response Body Example**:
  ```json
  {
    "total_users": 14,
    "active_users": 2,
    "verified_users": 12,
    "role_distribution": [
      {
        "role_name": "Super Admin",
        "count": 1
      },
      {
        "role_name": "Forest Officer",
        "count": 5
      }
    ],
    "user_growth_trend": [
      {
        "date_bucket": "2026-06-11",
        "count": 1
      },
      {
        "date_bucket": "2026-06-12",
        "count": 3
      }
    ]
  }
  ```
