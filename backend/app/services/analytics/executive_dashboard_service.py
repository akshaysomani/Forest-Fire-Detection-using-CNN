import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.analytics.kpi_service import kpi_service
from app.services.analytics.executive_metrics import executive_metrics
from app.services.analytics.strategic_analytics import strategic_analytics
from app.services.metrics_optimizer import metrics_optimizer

logger = logging.getLogger("analytics.executive_dashboard_service")


class ExecutiveDashboardService:
    async def get_executive_summary(self, db: AsyncSession, bypass_cache: bool = False) -> dict:
        """Fetch pre-aggregated KPI summaries, regional hazard indexes, and responder load ratios."""
        cache_key = "executive_dashboard_summary"

        async def fetch_fresh_summary():
            kpis = await kpi_service.get_current_kpi_summary(db, bypass_cache=True)
            hazard_level = await executive_metrics.get_fire_hazard_level(db)
            responders_ratio = await executive_metrics.get_active_responders_ratio(db)
            regional_risk = await strategic_analytics.get_regional_risk_index(db)

            return {
                "kpis": kpis,
                "regional_risk_index": regional_risk,
                "fire_hazard_level": hazard_level,
                "active_responders_ratio": responders_ratio
            }

        if bypass_cache:
            return await fetch_fresh_summary()

        return await metrics_optimizer.get_or_aggregate(cache_key, fetch_fresh_summary, ttl_seconds=30)


executive_dashboard_service = ExecutiveDashboardService()
