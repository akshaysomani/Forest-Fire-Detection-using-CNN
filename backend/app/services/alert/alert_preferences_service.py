import logging
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.alert import AlertPreference

logger = logging.getLogger("alert.alert_preferences_service")


class AlertPreferencesService:
    DEFAULT_CHANNELS = ["in_app", "email"]
    DEFAULT_MIN_SEVERITY = "Medium"

    async def get_user_preferences(self, db: AsyncSession, user_id: uuid.UUID) -> List[AlertPreference]:
        """
        Retrieves all notification preferences for a user.
        If no settings are defined in DB, defaults are returned.
        """
        query = select(AlertPreference).where(AlertPreference.user_id == user_id)
        result = await db.execute(query)
        preferences = list(result.scalars().all())

        if not preferences:
            logger.debug(f"No preferences found in DB for user {user_id}. Initializing default settings.")
            preferences = []
            for channel in self.DEFAULT_CHANNELS:
                default_pref = AlertPreference(
                    user_id=user_id,
                    channel=channel,
                    min_severity="High" if channel == "email" else "Medium",
                    enabled=True,
                    quiet_hours_start=None,
                    quiet_hours_end=None,
                )
                db.add(default_pref)
                preferences.append(default_pref)
            await db.flush()

        return preferences

    async def get_user_preference_for_channel(self, db: AsyncSession, user_id: uuid.UUID, channel: str) -> AlertPreference:
        """Fetch preference details for a specific channel."""
        query = select(AlertPreference).where(AlertPreference.user_id == user_id, AlertPreference.channel == channel)
        result = await db.execute(query)
        pref = result.scalar_one_or_none()

        if not pref:
            pref = AlertPreference(
                user_id=user_id,
                channel=channel,
                min_severity="High" if channel == "email" else "Medium",
                enabled=True,
                quiet_hours_start=None,
                quiet_hours_end=None,
            )
            db.add(pref)
            await db.flush()

        return pref

    async def update_user_preferences(
        self, db: AsyncSession, user_id: uuid.UUID, preferences_update: List[Dict[str, Any]]
    ) -> List[AlertPreference]:
        """
        Updates batch preferences configuration for a user.
        """
        updated_prefs = []
        for update_item in preferences_update:
            channel = update_item.get("channel")
            if not channel:
                continue

            pref = await self.get_user_preference_for_channel(db, user_id, channel)
            if "min_severity" in update_item:
                pref.min_severity = update_item["min_severity"]
            if "enabled" in update_item:
                pref.enabled = update_item["enabled"]
            if "quiet_hours_start" in update_item:
                pref.quiet_hours_start = update_item["quiet_hours_start"]
            if "quiet_hours_end" in update_item:
                pref.quiet_hours_end = update_item["quiet_hours_end"]

            db.add(pref)
            updated_prefs.append(pref)

        await db.flush()
        logger.info(f"Updated alert preferences for user {user_id}")
        return updated_prefs

    def is_in_quiet_hours(self, pref: AlertPreference, current_time_str: Optional[str] = None) -> bool:
        """
        Verifies if quiet hours are currently active for the preference record.
        Time parameter format expected: HH:MM
        """
        if not pref.quiet_hours_start or not pref.quiet_hours_end:
            return False

        if not current_time_str:
            # Get current time in UTC HH:MM
            now = datetime.now(timezone.utc)
            current_time_str = now.strftime("%H:%M")

        try:
            curr_h, curr_m = map(int, current_time_str.split(":"))
            start_h, start_m = map(int, pref.quiet_hours_start.split(":"))
            end_h, end_m = map(int, pref.quiet_hours_end.split(":"))

            curr_mins = curr_h * 60 + curr_m
            start_mins = start_h * 60 + start_m
            end_mins = end_h * 60 + end_m

            if start_mins <= end_mins:
                # Same day quiet window, e.g. 09:00 to 17:00
                return start_mins <= curr_mins <= end_mins
            else:
                # Midnight crossing quiet window, e.g. 22:00 to 06:00
                return curr_mins >= start_mins or curr_mins <= end_mins
        except Exception as e:
            logger.error(
                f"Error parsing quiet hours strings: start={pref.quiet_hours_start}, end={pref.quiet_hours_end}. Error: {e}"
            )
            return False


alert_preferences_service = AlertPreferencesService()
