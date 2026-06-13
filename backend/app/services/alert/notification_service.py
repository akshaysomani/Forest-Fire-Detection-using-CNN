import logging
from datetime import datetime, timezone
from typing import List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.alert import Alert, AlertNotification, AlertRecipient, AlertAuditLog
from app.services.alert.preference_manager import preference_manager
from app.services.alert.alert_preferences_service import alert_preferences_service
from app.services.alert.delivery_manager import delivery_manager

logger = logging.getLogger("alert.notification_service")


class NotificationService:
    async def send_alert_notifications(self, db: AsyncSession, alert: Alert) -> List[AlertNotification]:
        """
        Identify active users, check preferences (severity, quiet hours),
        generate recipients mapping and dispatch notifications via delivery manager.
        """
        logger.info(f"Preparing notifications for alert: {alert.id} (Severity: {alert.severity})")

        # 1. Fetch active users
        user_query = select(User).where(User.is_active == True).options(selectinload(User.roles))
        user_res = await db.execute(user_query)
        users = user_res.scalars().all()

        notifications_created = []

        for user in users:
            # Create a recipient link for tracking
            recipient = AlertRecipient(
                alert_id=alert.id,
                user_id=user.id
            )
            db.add(recipient)

            # Retrieve user preference settings
            preferences = await alert_preferences_service.get_user_preferences(db, user.id)

            for pref in preferences:
                # Check if notification is enabled and meets severity / quiet hours criteria
                should_notify = await preference_manager.should_notify_user(
                    db=db,
                    user_id=user.id,
                    channel=pref.channel,
                    alert_severity=alert.severity
                )

                if not should_notify:
                    # Let's see if quiet hours are the reason, so we can log it as pending/suppressed
                    in_quiet = alert_preferences_service.is_in_quiet_hours(pref)
                    if in_quiet:
                        # Log as pending due to quiet hours to dispatch later
                        notification = AlertNotification(
                            alert_id=alert.id,
                            recipient_id=user.id,
                            channel=pref.channel,
                            status="pending",
                            error_message="Quiet hours active"
                        )
                        db.add(notification)
                        notifications_created.append(notification)
                    continue

                # Create the notification log
                notification = AlertNotification(
                    alert_id=alert.id,
                    recipient_id=user.id,
                    channel=pref.channel,
                    status="pending"
                )
                db.add(notification)
                await db.flush()  # Populates notification.id

                # Resolve destination
                destination = user.email if pref.channel == "email" else str(user.id)
                if pref.channel == "sms":
                    # Fallback or stub phone
                    destination = "+15550199"

                subject = f"FOREST FIRE DETECTED [{alert.severity}]"

                # Trigger Delivery Manager
                success = await delivery_manager.deliver(
                    channel=pref.channel,
                    destination=destination,
                    message=alert.message,
                    subject=subject
                )

                # Update status based on delivery result
                if success:
                    notification.status = "sent"
                    notification.sent_at = datetime.now(timezone.utc)
                else:
                    notification.status = "failed"
                    notification.error_message = "Delivery failed"

                db.add(notification)
                notifications_created.append(notification)

                # Log notification dispatch in audit log
                audit = AlertAuditLog(
                    alert_id=alert.id,
                    user_id=user.id,
                    action="notification_dispatched" if success else "notification_failed",
                    details={
                        "notification_id": str(notification.id),
                        "channel": pref.channel,
                        "destination": destination,
                        "success": success
                    }
                )
                db.add(audit)

        await db.flush()
        logger.info(f"Dispatched {len(notifications_created)} notifications for Alert {alert.id}")
        return notifications_created


notification_service = NotificationService()
