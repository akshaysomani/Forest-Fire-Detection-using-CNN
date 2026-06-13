import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.analytics import KPIHistory, AnalyticsAuditLog
from app.services.analytics.kpi_calculator import kpi_calculator
from app.services.metrics_optimizer import metrics_optimizer

logger = logging.getLogger("analytics.kpi_service")


class KPIService:
    async def record_current_kpis(self, db: AsyncSession) -> Dict[str, float]:
        """Calculate and store all current KPIs in the historical log."""
        logger.info("Computing and recording latest platform KPIs...")
        now = datetime.now(timezone.utc)

        kpis = {
            "fire_detection_count": float(await kpi_calculator.get_fire_detection_count(db)),
            "detection_accuracy": float(await kpi_calculator.get_detection_accuracy(db)),
            "incident_resolution_time_min": float(await kpi_calculator.get_incident_resolution_time_min(db)),
            "alert_response_time_min": float(await kpi_calculator.get_alert_response_time_min(db)),
            "active_incidents": float(await kpi_calculator.get_active_incidents_count(db)),
            "user_activity_count": float(await kpi_calculator.get_user_activity_count(db)),
            "dataset_growth_bytes": float(await kpi_calculator.get_dataset_growth_bytes(db)),
            "model_performance_score": float(await kpi_calculator.get_model_performance_score(db)),
        }

        # Save to database
        for name, val in kpis.items():
            kpi_entry = KPIHistory(
                kpi_name=name,
                kpi_value=val,
                recorded_date=now
            )
            db.add(kpi_entry)

        # Audit Log
        audit = AnalyticsAuditLog(
            action="kpi_recorded",
            details={"recorded_kpis": list(kpis.keys()), "timestamp": now.isoformat()}
        )
        db.add(audit)
        await db.flush()

        logger.info(f"Recorded {len(kpis)} KPIs in history successfully.")
        return kpis

    async def get_current_kpi_summary(self, db: AsyncSession, bypass_cache: bool = False) -> Dict[str, Any]:
        """Retrieve the latest real-time computed KPIs, utilizing caching."""
        cache_key = "analytics_kpi_summary"

        async def fetch_fresh_kpis():
            return {
                "fire_detection_count": await kpi_calculator.get_fire_detection_count(db),
                "detection_accuracy": await kpi_calculator.get_detection_accuracy(db),
                "incident_resolution_time_min": await kpi_calculator.get_incident_resolution_time_min(db),
                "alert_response_time_min": await kpi_calculator.get_alert_response_time_min(db),
                "active_incidents": await kpi_calculator.get_active_incidents_count(db),
                "user_activity_count": await kpi_calculator.get_user_activity_count(db),
                "dataset_growth_bytes": await kpi_calculator.get_dataset_growth_bytes(db),
                "model_performance_score": await kpi_calculator.get_model_performance_score(db),
            }

        if bypass_cache:
            return await fetch_fresh_kpis()

        return await metrics_optimizer.get_or_aggregate(cache_key, fetch_fresh_kpis, ttl_seconds=30)

    async def get_historical_kpis(self, db: AsyncSession, kpi_name: str, days: int = 30) -> List[KPIHistory]:
        """Fetch historical records for a specific KPI over a time window."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = select(KPIHistory).where(
            and_(
                KPIHistory.kpi_name == kpi_name,
                KPIHistory.recorded_date >= cutoff,
                KPIHistory.deleted_at.is_(None)
            )
        ).order_by(KPIHistory.recorded_date.asc())
        
        res = await db.execute(query)
        return list(res.scalars().all())


kpi_service = KPIService()
