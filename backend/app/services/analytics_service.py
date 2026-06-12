from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.dashboard_repository import dashboard_repository
from app.services.trend_analyzer import trend_analyzer
from app.schemas.dashboard_schema import ModelUsageStat, UserGrowthData


class AnalyticsService:
    async def get_user_growth_trend(
        self, db: AsyncSession, days: int = 30
    ) -> List[UserGrowthData]:
        """Fetch user registration growth over a rolling time window."""
        raw = await dashboard_repository.get_user_growth_trend(db, days)
        filled = trend_analyzer.fill_missing_dates(raw, days)
        return [UserGrowthData(date_bucket=f["date_bucket"], count=f["count"]) for f in filled]

    async def get_detection_growth_trend(
        self, db: AsyncSession, days: int = 30
    ) -> List[dict]:
        """Fetch processed images/detections counts trend over a rolling window."""
        raw = await dashboard_repository.get_detection_trend(db, days)
        return trend_analyzer.fill_missing_dates(raw, days)

    async def get_model_usage_statistics(
        self, db: AsyncSession
    ) -> List[ModelUsageStat]:
        """Fetch CNN model usage logs grouped by name and version."""
        raw_stats = await dashboard_repository.get_model_usage_statistics(db)
        return [
            ModelUsageStat(
                model_name=item[0],
                model_version=item[1],
                count=item[2],
                average_confidence=item[3]
            )
            for item in raw_stats
        ]


analytics_service = AnalyticsService()
