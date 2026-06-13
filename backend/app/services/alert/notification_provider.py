import logging
import uuid
import asyncio
from typing import Protocol

logger = logging.getLogger("alert.notification_provider")


class NotificationProvider(Protocol):
    async def send(self, to: str, message: str, subject: str = "") -> bool:
        """Send a notification to a destination."""
        ...


class EmailNotificationProvider:
    async def send(self, to: str, message: str, subject: str = "") -> bool:
        """Simulate sending an email with network delay."""
        logger.info(f"[Email Provider] Sending email to: {to} | Subject: {subject}")
        # Simulate slight network delay
        await asyncio.sleep(0.05)
        logger.info(f"[Email Provider] Email successfully sent to: {to}")
        return True


class InAppNotificationProvider:
    async def send(self, to: str, message: str, subject: str = "") -> bool:
        """Simulate sending an in-app notification."""
        logger.info(f"[In-App Provider] Sending notification to user ID: {to} | Message: {message}")
        await asyncio.sleep(0.01)
        logger.info(f"[In-App Provider] In-app notification delivered to user: {to}")
        return True


class SMSNotificationProvider:
    async def send(self, to: str, message: str, subject: str = "") -> bool:
        """Simulate sending an SMS."""
        logger.info(f"[SMS Provider] Sending SMS to phone: {to} | Message: {message}")
        await asyncio.sleep(0.05)
        logger.info(f"[SMS Provider] SMS delivered to phone: {to}")
        return True


email_provider = EmailNotificationProvider()
in_app_provider = InAppNotificationProvider()
sms_provider = SMSNotificationProvider()
