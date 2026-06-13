# Prediction Operational Guide

This guide describes operational steps, runbooks, and configurations for forest fire detection predictions.

---

## 1. Triggering Predictions

### Real-Time Single Image Analysis
Upload an image with optional GPS coordinate parameters to run real-time inference:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/predictions" \
     -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
     -F "file=@/path/to/forest_smoke.jpg" \
     -F "latitude=45.1234" \
     -F "longitude=-122.5678"
```

### High-Volume Batch Processing
For bulk drone imagery uploads, submit a batch request:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/predictions/batch" \
     -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
     -F "files=@image1.jpg" \
     -F "files=@image2.jpg"
```
The response returns a `job_id`. Periodically poll the job status:
```bash
curl -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
     "http://127.0.0.1:8000/api/v1/predictions/batch/<JOB_ID>"
```

---

## 2. Risk Classification Rules

The risk engine classifies detections into danger zones based on model confidence parameters:

*   **Non-Fire Detections:** Assigned **Low** risk.
*   **Fire Detections:**
    *   `Confidence >= 85%`: Classified as **High** risk (requires immediate emergency dispatcher notifications).
    *   `Confidence >= 60%`: Classified as **Medium** risk (triggers automated drone sweep verifications).
    *   `Confidence < 60%`: Classified as **Low** risk (requires human supervisor inspections).

---

## 3. SLA & Operational Telemetry

Live metrics can be inspected using the stats endpoint:
```bash
curl -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
     "http://127.0.0.1:8000/api/v1/predictions/statistics"
```
*   **Target Latency SLA:** Single image forward pass <= 50ms.
*   **Throughput SLA:** Up to 1,200 images/minute under default hardware profiles.
