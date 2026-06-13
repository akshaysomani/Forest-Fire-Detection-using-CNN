import asyncio
import logging
from typing import Dict, List, Callable, Awaitable, Any

logger = logging.getLogger("alert.event_bus")


class EventBus:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], Awaitable[None]]]] = {}
        self._worker_task: Any = None
        self._running: bool = False

    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """Register a callback for a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed callback to event type: {event_type}")

    async def publish(self, event_type: str, payload: Dict[str, Any]):
        """Enqueue an event for processing."""
        event = {"event_type": event_type, "payload": payload}
        await self._queue.put(event)
        logger.debug(f"Published event '{event_type}' to queue")

    def start(self):
        """Start the background consumer task if not already running."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        logger.info("EventBus consumer background worker started.")

    async def stop(self):
        """Stop the background consumer worker and drain queue."""
        if not self._running:
            return
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("EventBus consumer background worker stopped.")

    async def _process_queue(self):
        """Worker loop that continuously fetches and dispatches events."""
        while self._running:
            try:
                event = await self._queue.get()
                event_type = event.get("event_type")
                payload = event.get("payload")

                if event_type in self._subscribers:
                    tasks = []
                    for callback in self._subscribers[event_type]:
                        tasks.append(self._run_callback(callback, payload))
                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)

                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in EventBus worker loop: {e}", exc_info=True)

    async def _run_callback(self, callback: Callable[[Dict[str, Any]], Awaitable[None]], payload: Dict[str, Any]):
        try:
            await callback(payload)
        except Exception as e:
            logger.error(f"Error executing event subscription callback: {e}", exc_info=True)


# Global singleton instance of EventBus
event_bus = EventBus()
