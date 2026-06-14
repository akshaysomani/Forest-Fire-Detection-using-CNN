import logging
from typing import Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.alert import Alert, AlertNotification, AlertAcknowledgement
from app.services.alert.alert_monitor import alert_monitor
from app.services.alert.notification_metrics import notification_metrics

logger = logging.getLogger("alert.alert_observability_service")


class AlertObservabilityService:
    async def get_observability_metrics(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Compile database-wide telemetry metrics for alerts, notifications, and response times.
        """
        try:
            # 1. Alert Status Counts
            status_query = select(Alert.status, func.count(Alert.id)).where(Alert.deleted_at.is_(None)).group_by(Alert.status)
            status_res = await db.execute(status_query)
            status_map = {row[0]: row[1] for row in status_res.all()}

            # 2. Alert Severity Counts
            severity_query = (
                select(Alert.severity, func.count(Alert.id)).where(Alert.deleted_at.is_(None)).group_by(Alert.severity)
            )
            severity_res = await db.execute(severity_query)
            severity_map = {row[0]: row[1] for row in severity_res.all()}

            # 3. Notification Channel Status Counts
            notif_query = select(
                AlertNotification.channel, AlertNotification.status, func.count(AlertNotification.id)
            ).group_by(AlertNotification.channel, AlertNotification.status)
            notif_res = await db.execute(notif_query)
            notif_breakdown = {}
            for channel, status, count in notif_res.all():
                if channel not in notif_breakdown:
                    notif_breakdown[channel] = {}
                notif_breakdown[channel][status] = count

            # 4. Average Acknowledgement Latency (in seconds)
            # Fetch alert creation and acknowledgement creation times
            ack_time_query = (
                select(Alert.created_at, AlertAcknowledgement.created_at)
                .join(AlertAcknowledgement, Alert.id == AlertAcknowledgement.alert_id)
                .where(and_(AlertAcknowledgement.action == "acknowledge", Alert.deleted_at.is_(None)))
            )
            ack_time_res = await db.execute(ack_time_query)
            ack_times = ack_time_res.all()

            total_latency_seconds = 0.0
            ack_count = len(ack_times)
            for alert_created, ack_created in ack_times:
                diff = ack_created - alert_created
                total_latency_seconds += diff.total_seconds()

            avg_ack_latency = (total_latency_seconds / ack_count) if ack_count > 0 else 0.0

            # 5. Combine with in-memory counter snapshots
            mem_summary = alert_monitor.get_monitoring_summary()
            notif_mem_summary = notification_metrics.get_metrics_summary()

            return {
                "active_alerts": status_map.get("active", 0),
                "acknowledged_alerts": status_map.get("acknowledged", 0),
                "resolved_alerts": status_map.get("resolved", 0),
                "escalated_alerts": status_map.get("escalated", 0),
                "severity_counts": {
                    "Critical": severity_map.get("Critical", 0),
                    "High": severity_map.get("High", 0),
                    "Medium": severity_map.get("Medium", 0),
                    "Low": severity_map.get("Low", 0),
                    "Informational": severity_map.get("Informational", 0),
                },
                "notifications": notif_breakdown,
                "average_acknowledgement_time_seconds": avg_ack_latency,
                "runtime_counters": {
                    "alerts_evaluated": mem_summary.get("alerts_evaluated", 0),
                    "alerts_triggered": mem_summary.get("alerts_triggered", 0),
                    "escalations_triggered": mem_summary.get("escalations_triggered", 0),
                    "notif_in_memory": notif_mem_summary,
                },
            }
        except Exception as e:
            logger.error(f"Error compiling observability metrics: {e}", exc_info=True)
            return {"error": str(e)}


alert_observability_service = AlertObservabilityService()
