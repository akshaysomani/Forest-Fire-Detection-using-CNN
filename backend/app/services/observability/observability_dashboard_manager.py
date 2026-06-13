"""
Observability Dashboard Manager - Generates combined operational, reliability,
infrastructure, and executive summaries.

Orchestrates all observability services to produce comprehensive
dashboard views for different stakeholder levels.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.observability.platform_health_manager import platform_health_manager
from app.services.observability.slo_service import slo_service
from app.services.observability.apm_service import apm_service
from app.services.observability.logging_service import logging_service
from app.services.observability.availability_tracker import availability_tracker
from app.services.observability.reliability_alert_service import reliability_alert_service
from app.services.observability.dashboard_adapter import dashboard_adapter

logger = logging.getLogger("observability.dashboard_manager")


class ObservabilityDashboardManager:
    """
    Generates comprehensive observability dashboards combining data
    from all observability subsystems.
    """

    async def get_operational_dashboard(
        self,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Generate the operational dashboard view.
        Shows real-time health, APM metrics, and recent alerts.
        """
        health = await platform_health_manager.get_platform_health(db)
        apm_summary = await apm_service.get_apm_summary(db, hours=1)
        log_stats = await logging_service.get_log_statistics(db)
        recent_alerts = reliability_alert_service.get_alert_history(limit=10)

        return {
            "dashboard_type": "operational",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "platform_health": health,
            "apm": apm_summary,
            "log_statistics": log_stats,
            "recent_alerts": recent_alerts,
        }

    async def get_reliability_dashboard(
        self,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Generate the reliability dashboard view.
        Shows SLO compliance, error budgets, and availability trends.
        """
        slo_results = await slo_service.evaluate_all_slos(db)
        uptime = availability_tracker.get_uptime_summary()

        # Check for SLO violations
        alerts = reliability_alert_service.check_all_slos(slo_results)

        # Format for visualization
        slo_chart = dashboard_adapter.format_slo_compliance(slo_results)
        availability_chart = dashboard_adapter.format_availability(uptime)

        return {
            "dashboard_type": "reliability",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "slo_compliance": slo_results,
            "slo_visualization": slo_chart,
            "availability": uptime,
            "availability_visualization": availability_chart,
            "triggered_alerts": alerts,
        }

    async def get_executive_summary(
        self,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Generate a high-level executive summary.
        Shows key metrics, overall health, and compliance status.
        """
        health = await platform_health_manager.get_platform_health(db)
        slo_results = await slo_service.evaluate_all_slos(db)
        apm = await apm_service.get_throughput(db, hours=24)

        return {
            "dashboard_type": "executive",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_status": health.get("status", "unknown"),
            "api_status": health.get("api_status", "unknown"),
            "slo_compliant": slo_results.get("overall_compliant", False),
            "availability_24h": availability_tracker.get_availability_percentage(
                window_minutes=1440
            ),
            "throughput_24h": apm,
            "error_budgets": slo_results.get("error_budgets", {}),
        }


# Module-level singleton
observability_dashboard_manager = ObservabilityDashboardManager()
