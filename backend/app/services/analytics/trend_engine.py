import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.detection import Detection
from app.models.alert import Alert
from app.models.incident import Incident
from app.services.analytics.trend_analyzer import trend_analyzer
from app.services.analytics.historical_analysis import historical_analysis

logger = logging.getLogger("analytics.trend_engine")


class TrendEngine:
    async def get_detection_trends(self, db: AsyncSession, days: int = 30) -> List[Dict[str, Any]]:
        """Fetch daily counts of fire detections with their 7-day moving average."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        # SQLite vs Postgres compatible date extract
        date_expr = func.strftime("%Y-%m-%d", Detection.created_at)
        query = select(
            date_expr.label("date_bucket"),
            func.count(Detection.id)
        ).where(
            and_(
                Detection.prediction_label == "fire",
                Detection.created_at >= cutoff,
                Detection.deleted_at.is_(None)
            )
        ).group_by("date_bucket").order_by("date_bucket")

        res = await db.execute(query)
        raw_data = [(r[0], r[1]) for r in res.all()]
        
        # Fill missing dates to keep charts contiguous
        filled = trend_analyzer.fill_missing_dates(raw_data, days)
        
        # Add moving average
        moving_avgs = trend_analyzer.calculate_moving_average(filled, window_size=7)
        
        result = []
        for i, item in enumerate(filled):
            result.append({
                "date": item["date_bucket"],
                "detections_count": item["value"],
                "moving_average_7d": moving_avgs[i]["value"]
            })
        return result

    async def get_incident_trends(self, db: AsyncSession, days: int = 30) -> List[Dict[str, Any]]:
        """Fetch daily counts of incidents logged."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        date_expr = func.strftime("%Y-%m-%d", Incident.created_at)

        query = select(
            date_expr.label("date_bucket"),
            func.count(Incident.id)
        ).where(
            and_(
                Incident.created_at >= cutoff,
                Incident.deleted_at.is_(None)
            )
        ).group_by("date_bucket").order_by("date_bucket")

        res = await db.execute(query)
        raw_data = [(r[0], r[1]) for r in res.all()]
        filled = trend_analyzer.fill_missing_dates(raw_data, days)

        return [
            {"date": f["date_bucket"], "incidents_count": int(f["value"])}
            for f in filled
        ]

    async def get_all_trends_summary(self, db: AsyncSession, days: int = 30) -> Dict[str, Any]:
        """Compile seasonal, regional, and timeline trends into a single response."""
        detections = await self.get_detection_trends(db, days)
        incidents = await self.get_incident_trends(db, days)
        seasons = await historical_analysis.get_seasonal_trends(db, days=365)
        regions = await historical_analysis.get_regional_trends(db, days=days)

        return {
            "timeframe_days": days,
            "timeline": {
                "detections": detections,
                "incidents": incidents
            },
            "seasonal_distribution": seasons,
            "regional_distribution": regions
        }


trend_engine = TrendEngine()
