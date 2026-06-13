# Phase 1: Alert System Audit Report

## 1. Executive Summary
An audit of the Forest Fire Detection application was performed to evaluate its alerting capabilities. While the application successfully processes images and determines classification labels (Module 6), it completely lacks an **Alert Management System**. Detections remain passive database rows, and no notifications are dispatched to emergency response teams.

This audit highlights the gaps, reliability issues, and technical debt that will be resolved by the Module 7 implementation.

---

## 2. Identified Inefficiencies & Gaps

### A. Passive Detection Rows (No Generation)
*   **Issue:** The backend runs CNN inferences and saves results to the `detections` table, but there is no engine to inspect results and spawn emergency alerts automatically.
*   **Risk:** Wildfires go unnoticed in real-time, defeating the operational purpose of drone/camera monitoring feeds.
*   **Recommendation:** Implement an asynchronous `AlertEngine` that inspects high-confidence fire detections.

### B. Lack of Database Tables
*   **Issue:** The database does not hold tables for alerts, event states, user preferences, notification logs, acknowledgements, or escalations.
*   **Risk:** No audit trail of incident ownership, accountability, or delivery tracking.
*   **Recommendation:** Build SQLAlchemy schemas for `alerts`, `alert_events`, `alert_notifications`, `alert_preferences`, `alert_recipients`, `alert_acknowledgements`, and `alert_audit_logs`.

### C. Coupled Notification Workflows
*   **Issue:** If notifications (like emails or SMS) are executed synchronously during prediction requests, any delivery failure (due to external SMTP timeouts) will block or crash the inference pipeline.
*   **Risk:** High API latency, lost predictions, and connection exhaustion.
*   **Recommendation:** Decouple delivery using an in-memory pub-sub `EventBus` running background queue workers.

### D. Missing Escalation Mechanisms
*   **Issue:** Active alerts are not acknowledged, and there is no mechanism to escalate critical unacknowledged warnings to supervisors.
*   **Risk:** High-priority incidents remain unaddressed if a single dispatcher is away or inactive.
*   **Recommendation:** Create an `EscalationService` that triggers alerts to next-in-line responders if not acknowledged within configurable time bounds (e.g. 5–15 minutes).

### E. No Preference Control
*   **Issue:** Users have no control over notification channels, severity levels, or quiet hours.
*   **Risk:** Responder notification fatigue, leading to missed critical alerts or unwanted disturbances during off-shift hours.
*   **Recommendation:** Implement user-level `AlertPreference` models and preference endpoints.

---

## 3. Prioritized Recommendations

| Priority | Phase / Action | Description | Impact |
| :--- | :--- | :--- | :--- |
| **P0** | Database Models (Phase 3) | Create alert-related SQLAlchemy tables and index mappings. | Establishes the foundational state registry. |
| **P0** | Event Bus & Engine (Phases 4 & 9) | Decouple alert generation and consumption using an async event bus. | Prevents SMTP delays from stalling inference threads. |
| **P1** | Channels & Delivery (Phases 5 & 6) | Build email/in-app notification providers and severity classifiers. | Delivers actual warnings to emergency responders. |
| **P1** | Ownership & Preference (Phases 7 & 8) | Implement alert acceptance, resolution states, and user channels/quiet hours. | Enforces accountability and mitigates responder notification fatigue. |
| **P2** | Monitoring & Observability (Phase 11) | Track metrics like time-to-acknowledge, dispatch failures, and alert volume. | Alerts operators of delivery system anomalies. |
