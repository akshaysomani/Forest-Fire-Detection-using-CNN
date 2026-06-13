import asyncio
import logging
from datetime import datetime, timezone
from app.core.database import SessionLocal
from app.services.analytics.analytics_aggregator import analytics_aggregator
from app.services.analytics.kpi_service import kpi_service

logger = logging.getLogger("analytics.aggregation_scheduler")


class AggregationScheduler:
    def __init__(self, run_interval_seconds: float = 300.0):
        self._interval = run_interval_seconds
        self._task: asyncio.Task = None
        self._running = False

    def start(self):
        """Launches the background analytics scheduler loop."""
        if self._running:
            return
        self._running = True
        logger.info(f"Launching Analytics Aggregation Scheduler (Interval: {self._interval}s)...")
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        """Stops the scheduler and cancels the background task."""
        if not self._running:
            return
        self._running = False
        logger.info("Stopping Analytics Aggregation Scheduler...")
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Analytics Aggregation Scheduler successfully stopped.")

    async def _loop(self):
        while self._running:
            try:
                await asyncio.sleep(self._interval)
                await self.run_aggregations()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Analytics Scheduler loop: {e}", exc_info=True)

    async def run_aggregations(self):
        """Execute a pass of logging active KPIs and compiling period summaries."""
        async with SessionLocal() as db:
            try:
                # 1. Take a real-time snapshot of current KPIs
                await kpi_service.record_current_kpis(db)

                # 2. Run aggregations for current periods
                now = datetime.now(timezone.utc)
                await analytics_aggregator.aggregate_daily(db, now)
                await analytics_aggregator.aggregate_weekly(db, now)
                await analytics_aggregator.aggregate_monthly(db, now.year, now.month)

                # Determine quarter
                quarter = (now.month - 1) // 3 + 1
                await analytics_aggregator.aggregate_quarterly(db, now.year, quarter)
                await analytics_aggregator.aggregate_annual(db, now.year)

                await db.commit()
                logger.debug("Analytics scheduled aggregation run completed successfully.")
            except Exception as e:
                await db.rollback()
                logger.error(f"Database error during analytics aggregations: {e}", exc_info=True)


aggregation_scheduler = AggregationScheduler()
