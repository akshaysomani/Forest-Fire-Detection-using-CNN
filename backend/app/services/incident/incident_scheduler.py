import asyncio
import logging
from app.core.database import SessionLocal
from app.services.alert.event_bus import event_bus
from app.services.incident.emergency_workflow_engine import emergency_workflow_engine
from app.services.incident.automation_service import automation_service

logger = logging.getLogger("incident.incident_scheduler")


class IncidentScheduler:
    def __init__(self, check_interval_seconds: float = 30.0):
        self._check_interval = check_interval_seconds
        self._task: asyncio.Task = None
        self._running = False

    def start(self):
        """Binds event subscribers and launches the background scheduler loop."""
        if self._running:
            return

        self._running = True
        logger.info("Subscribing EmergencyWorkflowEngine to Alert Event Bus...")
        event_bus.subscribe("alert_generated", emergency_workflow_engine.handle_alert_generated)

        logger.info(f"Launching Incident Scheduler background loop (Interval: {self._check_interval}s)...")
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        """Stops the scheduler and cancels the background task."""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping Incident Scheduler background loop...")
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Incident Scheduler background loop successfully stopped.")

    async def _loop(self):
        """Infinite loop checking SLAs and auto dispatches."""
        while self._running:
            try:
                await asyncio.sleep(self._check_interval)
                await self.run_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Incident Scheduler loop: {e}", exc_info=True)

    async def run_checks(self):
        """Executes a single check pass across automation services."""
        async with SessionLocal() as db:
            try:
                # 1. Run SLA check & automatic escalation
                await automation_service.run_sla_and_escalation_checks(db)

                # 2. Run auto-dispatch check for open incidents
                await automation_service.run_auto_dispatch_checks(db)

                await db.commit()
            except Exception as e:
                await db.rollback()
                logger.error(f"Database error during scheduled incident check pass: {e}", exc_info=True)


# Global singleton instance of scheduler
incident_scheduler = IncidentScheduler()
