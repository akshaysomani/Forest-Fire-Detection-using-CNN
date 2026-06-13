# Prediction API Reference

All prediction endpoints are served under `/api/v1/predictions`.

---

## 1. Endpoints Reference

### `POST /predictions`
Analyze a single uploaded image.
*   **Permissions:** `upload_images`
*   **Request Form-Data:**
    *   `file`: Binary file upload (Required)
    *   `latitude`: Float (Optional)
    *   `longitude`: Float (Optional)
*   **Response (201 Created):**
```json
{
  "detection": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "image_path": "detections/img.jpg",
    "filename": "img.jpg",
    "prediction_label": "fire",
    "confidence": 0.94,
    "model_name": "custom_cnn",
    "model_version": "1.0.0",
    "latitude": 12.97,
    "longitude": 77.59,
    "created_at": "2026-06-13T12:00:00Z",
    "updated_at": "2026-06-13T12:00:00Z"
  },
  "risk_level": "High",
  "probabilities": {
    "non-fire": 0.06,
    "fire": 0.94
  },
  "processing_duration_seconds": 0.045
}
```

### `POST /predictions/batch`
Queue multiple images for background batch processing.
*   **Permissions:** `upload_images`
*   **Request Form-Data:**
    *   `files`: List of binary file uploads (Required)
*   **Response (202 Accepted):**
```json
{
  "success": true,
  "message": "Batch prediction job successfully queued.",
  "job_id": "a908be56-02e4-4fb0-85f6-db23c1fd33b8",
  "total_images": 25
}
```

### `GET /predictions/batch/{job_id}`
Query progress details of a batch job.
*   **Permissions:** `view_predictions`
*   **Response (200 OK):**
```json
{
  "job_id": "a908be56-02e4-4fb0-85f6-db23c1fd33b8",
  "status": "processing",
  "total_count": 25,
  "success_count": 18,
  "failed_count": 0,
  "results": [
    {
      "detection_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "filename": "drone_1.jpg",
      "prediction_label": "fire",
      "confidence": 0.97
    }
  ],
  "errors": []
}
```

### `GET /predictions`
List historical prediction records (paginated).
*   **Permissions:** `view_predictions`
*   **Query Parameters:**
    *   `skip`: Integer (Default: 0)
    *   `limit`: Integer (Default: 100)
*   **Response (200 OK):**
```json
{
  "total": 128,
  "skip": 0,
  "limit": 100,
  "items": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "prediction_label": "non-fire",
      "confidence": 0.99
    }
  ]
}
```

### `GET /predictions/statistics`
Retrieve system-wide prediction counts, average confidence, and latency telemetry.
*   **Permissions:** `view_predictions`
*   **Response (200 OK):**
```json
{
  "total_predictions": 1280,
  "fire_count": 340,
  "non_fire_count": 940,
  "average_confidence": 0.912,
  "average_latency_seconds": 0.048,
  "accuracy_percentage": 94.5
}
```
