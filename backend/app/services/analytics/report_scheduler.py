import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select, and_
from app.core.database import SessionLocal
from app.models.analytics import ReportDefinition
from app.services.analytics.reporting_service import reporting_service

logger = logging.getLogger("analytics.report_scheduler")


class ReportScheduler:
    def __init__(self, run_interval_seconds: float = 60.0):
        self._interval = run_interval_seconds
        self._task: asyncio.Task = None
        self._running = False
        self._last_run_date = None

    def start(self):
        """Launches the background reporting cron loop."""
        if self._running:
            return
        self._running = True
        logger.info(f"Launching Report Scheduler background worker (Interval: {self._interval}s)...")
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        """Stops the scheduler and cancels the background task."""
        if not self._running:
            return
        self._running = False
        logger.info("Stopping Report Scheduler background worker...")
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Report Scheduler background worker successfully stopped.")

    async def _loop(self):
        while self._running:
            try:
                await asyncio.sleep(self._interval)
                await self.check_and_run_reports()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Report Scheduler loop: {e}", exc_info=True)

    async def check_and_run_reports(self):
        """Check report definitions and trigger any scheduled runs (simulating daily runs at midnight)."""
        now = datetime.now(timezone.utc)
        current_date_str = now.strftime("%Y-%m-%d")

        # Prevent double-runs within the same day for daily reports
        if self._last_run_date == current_date_str:
            return

        async with SessionLocal() as db:
            try:
                # Find all scheduled report templates
                query = select(ReportDefinition).where(
                    and_(
                        ReportDefinition.is_scheduled == True,
                        ReportDefinition.deleted_at.is_(None)
                    )
                )
                res = await db.execute(query)
                definitions = res.scalars().all()

                if not definitions:
                    return

                logger.info(f"Triggering {len(definitions)} scheduled report templates...")
                for df in definitions:
                    # Run scheduled reports under System Admin context (None user)
                    try:
                        await reporting_service.generate_report(
                            db=db,
                            report_type=df.report_type,
                            export_format="PDF",
                            parameters=df.parameters,
                            definition_id=df.id,
                            user_id=None
                        )
                    except Exception as e:
                        logger.error(f"Failed to execute scheduled report definition {df.id}: {e}")

                await db.commit()
                self._last_run_date = current_date_str
            except Exception as e:
                await db.rollback()
                logger.error(f"Error checking scheduled reports: {e}", exc_info=True)


report_scheduler = ReportScheduler()
