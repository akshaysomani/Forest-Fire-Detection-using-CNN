# Alert System - Production Readiness Checklist

This checklist acts as a guide to verify system deployments before moving to staging/production.

- [ ] **Database Indexes**: Verify indexes exist on foreign keys (`detection_id`, `recipient_id`, `alert_id`) and filterable fields (`status`, `severity`).
- [ ] **Environment Variables**: Configure real SMTP credentials or Twilio API keys in the `.env` settings to replace the notification stubs.
- [ ] **Lifespan Hooks**: Confirm the Alert Event Bus initializes correctly in container entry points.
- [ ] **SLA Cron Cronjobs**: Configure a celery beat scheduler or a system cron job to run the `escalation_service.check_and_escalate_alerts()` scan every 5 minutes.
- [ ] **Docker Mounts**: Confirm that persistent logs are mapped to permanent storage mounts.
- [ ] **Sentry Monitoring**: Register key alert event handlers to capture and notify on background delivery failures.
