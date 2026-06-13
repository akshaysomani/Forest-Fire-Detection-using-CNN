import re
import logging

logger = logging.getLogger("alert.user_notification_settings")

TIME_FORMAT_REGEX = re.compile(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")


class UserNotificationSettings:
    @staticmethod
    def validate_time_format(time_str: str) -> bool:
        """Validates if a string matches HH:MM format."""
        if not time_str:
            return False
        return bool(TIME_FORMAT_REGEX.match(time_str))

    @staticmethod
    def validate_severity_level(severity: str) -> bool:
        """Validates if a severity matches allowed levels."""
        allowed = {"Critical", "High", "Medium", "Low", "Informational"}
        return severity in allowed


user_notification_settings = UserNotificationSettings()
