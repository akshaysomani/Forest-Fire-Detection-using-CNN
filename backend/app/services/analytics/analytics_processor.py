import logging
import uuid
from typing import Dict, Any
from app.core.database import SessionLocal
from app.models.analytics import AnalyticsEvent

logger = logging.getLogger("analytics.analytics_processor")


class AnalyticsProcessor:
    async def log_event(self, event_type: str, event_source: str, payload: Dict[str, Any], user_id: uuid.UUID = None) -> None:
        """Helper to insert an analytical event log."""
        async with SessionLocal() as db:
            try:
                event = AnalyticsEvent(
                    event_type=event_type,
                    event_source=event_source,
                    user_id=user_id,
                    payload=payload
                )
                db.add(event)
                await db.commit()
                logger.debug(f"Logged analytics event: {event_type} from {event_source}")
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to log analytics event: {e}")

    async def handle_alert_generated(self, payload: Dict[str, Any]) -> None:
        await self.log_event(
            event_type="alert_generated",
            event_source="alert_system",
            payload=payload
        )

    async def handle_alert_escalated(self, payload: Dict[str, Any]) -> None:
        await self.log_event(
            event_type="alert_escalated",
            event_source="alert_system",
            payload=payload
        )

    async def handle_geofence_breached(self, payload: Dict[str, Any]) -> None:
        await self.log_event(
            event_type="geofence_breached",
            event_source="gis_system",
            payload=payload
        )

    async def handle_inference_completed(self, payload: Dict[str, Any]) -> None:
        user_id_str = payload.get("user_id")
        user_id = uuid.UUID(user_id_str) if user_id_str else None
        await self.log_event(
            event_type="inference_completed",
            event_source="inference_engine",
            payload=payload,
            user_id=user_id
        )


analytics_processor = AnalyticsProcessor()
