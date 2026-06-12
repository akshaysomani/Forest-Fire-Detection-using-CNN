import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.system_metrics import system_metrics

logger = logging.getLogger("health_service")


class HealthService:
    async def check_database_health(self, db: AsyncSession) -> bool:
        """Pings the database with a lightweight select 1 check."""
        try:
            # We must use text() for raw sql execute statements in SQLAlchemy 2.x
            res = await db.execute(text("SELECT 1"))
            val = res.scalar()
            return val == 1
        except Exception as e:
            logger.critical(f"Database health check failed: {e}")
            return False

    def check_storage_health(self, path: str = ".") -> bool:
        """Verifies if the disk storage capacity is safe (under 95% usage)."""
        try:
            metrics = system_metrics.get_storage_usage(path)
            return metrics["percentage_used"] < 95.0
        except Exception as e:
            logger.error(f"Storage capacity health check failed: {e}")
            return False


health_service = HealthService()
