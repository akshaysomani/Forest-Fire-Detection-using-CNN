# Alert System - API Reference Guide

Base Prefix: `/api/v1/alerts`

## 1. Endpoints List

### `GET /api/v1/alerts`
Retrieves a paginated list of alerts.
- **Role**: `view_alerts`
- **Query Parameters**:
  - `skip` (default 0): pagination offset
  - `limit` (default 100): maximum records count
  - `status`: filter (active, acknowledged, resolved, escalated)
  - `severity`: filter (Critical, High, Medium, Low, Informational)
- **Response** (`200 OK`):
```json
{
  "alerts": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "detection_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "severity": "Critical",
      "status": "active",
      "message": "POTENTIAL WILDFIRE DETECTED...",
      "created_at": "2026-06-13T12:00:00Z",
      "updated_at": "2026-06-13T12:00:00Z"
    }
  ],
  "total_count": 1
}
```

### `POST /api/v1/alerts`
Generates a manual alert.
- **Role**: `manage_platform_settings`
- **Payload**:
```json
{
  "severity": "High",
  "message": "Smoke plume reported near forest outpost.",
  "detection_id": null,
  "payload": {}
}
```
- **Response** (`201 Created`): Returns generated `AlertResponse` object.

### `PATCH /api/v1/alerts/{id}/acknowledge`
Acknowledge an active/escalated alert.
- **Role**: `view_alerts`
- **Payload**:
```json
{
  "notes": "Dispatching ground team to investigate."
}
```
- **Response** (`200 OK`): Returns updated `AlertResponse`.

### `PATCH /api/v1/alerts/{id}/resolve`
Resolve an alert.
- **Role**: `view_alerts`
- **Payload**:
```json
{
  "notes": "False alarm. Controlled agricultural burn confirmed."
}
```
- **Response** (`200 OK`): Returns updated `AlertResponse`.

### `GET /api/v1/alerts/statistics`
Fetch observability telemetry counts and average response times.
- **Role**: `view_alerts`
- **Response** (`200 OK`):
```json
{
  "active_alerts": 1,
  "acknowledged_alerts": 2,
  "resolved_alerts": 10,
  "escalated_alerts": 0,
  "severity_counts": {
    "Critical": 1,
    "High": 3,
    "Medium": 5,
    "Low": 2,
    "Informational": 0
  },
  "average_acknowledgement_time_seconds": 124.5
}
```

### `GET /api/v1/alerts/preferences`
Fetch user notification options.
- **Response** (`200 OK`):
```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "channel": "email",
    "min_severity": "High",
    "enabled": true,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "06:00",
    "created_at": "2026-06-13T12:00:00Z"
  }
]
```

### `PUT /api/v1/alerts/preferences`
Batch update preferences.
- **Payload**: Array of channel updates:
```json
[
  {
    "channel": "email",
    "min_severity": "Critical",
    "enabled": false
  }
]
```
- **Response** (`200 OK`): List of updated preferences.
