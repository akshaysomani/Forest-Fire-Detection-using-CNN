# Decoupled Event System - Event Processing Guide

This document describes the design, concurrency, and async worker loops in our decoupled alert architecture.

## 1. Concurrency Architecture
Fast SMTP servers or SMS gateways can add 1-5 seconds of network delay. Decoupling ensures that CNN prediction threads are not blocked by SMTP/SMS dispatches.

```text
Prediction Thread -> evaluate_detection -> event_bus.publish("alert_generated", payload)
                                             |
                                     (asyncio.Queue)
                                             |
                                             v
Background Consumer Worker (EventBus Loop) -> subscribers -> dispatch notification provider
```

## 2. Event Bus Implementation
- **Queueing Structure**: Uses `asyncio.Queue` which is thread-safe on the event loop.
- **Worker Management**: Wrapped in `QueueManager` to initialize listeners (`handle_alert_generated`, `handle_alert_escalated`) and start the loop task during FastAPI `lifespan` startup, and cancel the loop gracefully on shutdown.
- **Transaction Safety**: Because the worker executes inside background tasks, it instantiates its own `SessionLocal` database context managers to avoid resource leaks and ensure database queries commit independently.
