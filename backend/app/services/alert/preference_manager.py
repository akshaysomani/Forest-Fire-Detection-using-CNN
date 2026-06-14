import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.alert.alert_preferences_service import alert_preferences_service
from app.services.alert.user_notification_settings import user_notification_settings

logger = logging.getLogger("alert.preference_manager")


class PreferenceManager:
    @staticmethod
    async def should_notify_user(db: AsyncSession, user_id: uuid.UUID, channel: str, alert_severity: str) -> bool:
        """
        Calculates if a user should be notified on a given channel for an alert severity.
        Verifies: channel is enabled, meets severity thresholds, and is NOT in quiet hours.
        """
        try:
            pref = await alert_preferences_service.get_user_preference_for_channel(db=db, user_id=user_id, channel=channel)

            # 1. Check if channel is enabled
            if not pref.enabled:
                logger.debug(f"Notification suppressed: Channel {channel} disabled for user {user_id}")
                return False

            # 2. Check severity threshold
            severity_ranks = {"Critical": 5, "High": 4, "Medium": 3, "Low": 2, "Informational": 1}
            pref_rank = severity_ranks.get(pref.min_severity, 3)
            alert_rank = severity_ranks.get(alert_severity, 3)

            if alert_rank < pref_rank:
                logger.debug(
                    f"Notification suppressed: Alert severity {alert_severity} (rank {alert_rank}) "
                    f"is lower than minimum {pref.min_severity} (rank {pref_rank}) for user {user_id}"
                )
                return False

            # 3. Check quiet hours
            if alert_preferences_service.is_in_quiet_hours(pref):
                logger.debug(f"Notification suppressed: User {user_id} channel {channel} is in quiet hours")
                return False

            return True
        except Exception as e:
            logger.error(f"Error checking notification status for user {user_id}: {e}", exc_info=True)
            # Default to True as a fail-safe in production for Critical/High alerts
            return alert_severity in ["Critical", "High"]


preference_manager = PreferenceManager()
