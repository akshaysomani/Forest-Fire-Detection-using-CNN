import logging
from app.services.alert.notification_provider import email_provider, in_app_provider, sms_provider

logger = logging.getLogger("alert.delivery_manager")


class DeliveryManager:
    async def deliver(self, channel: str, destination: str, message: str, subject: str = "") -> bool:
        """
        Route delivery payload to the correct channel provider.
        Returns True if sent successfully, False otherwise.
        """
        logger.debug(f"Routing delivery to channel: {channel} to destination: {destination}")
        try:
            channel_lower = channel.lower()
            if channel_lower == "email":
                return await email_provider.send(to=destination, message=message, subject=subject)
            elif channel_lower == "in_app" or channel_lower == "inapp":
                return await in_app_provider.send(to=destination, message=message)
            elif channel_lower == "sms":
                return await sms_provider.send(to=destination, message=message)
            else:
                logger.warning(f"Unsupported delivery channel requested: {channel}")
                return False
        except Exception as e:
            logger.error(f"Error during notification delivery on channel {channel}: {e}", exc_info=True)
            return False


delivery_manager = DeliveryManager()
