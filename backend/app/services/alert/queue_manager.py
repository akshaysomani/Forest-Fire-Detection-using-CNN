import logging
from app.services.alert.event_bus import event_bus
from app.services.alert.alert_event_handler import handle_alert_generated, handle_alert_generated as handle_alert_escalated

logger = logging.getLogger("alert.queue_manager")


class QueueManager:
    @staticmethod
    def start_alert_queue():
        """Binds subscribers and starts background worker."""
        logger.info("Initializing Alert Event Bus and registering handlers...")
        event_bus.subscribe("alert_generated", handle_alert_generated)
        event_bus.subscribe("alert_escalated", handle_alert_escalated)
        
        # GIS / Geofencing event subscribers registration
        from app.services.gis.location_event_handler import handle_alert_generated_gis, handle_geofence_breach_event
        event_bus.subscribe("alert_generated", handle_alert_generated_gis)
        event_bus.subscribe("geofence_breached", handle_geofence_breach_event)
        
        event_bus.start()
        logger.info("Alert Event Bus successfully started.")

    @staticmethod
    async def stop_alert_queue():
        """Stops background worker and cleans up resources."""
        logger.info("Stopping Alert Event Bus...")
        await event_bus.stop()
        logger.info("Alert Event Bus successfully stopped.")


queue_manager = QueueManager()
