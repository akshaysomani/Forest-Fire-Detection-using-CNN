# Notification Systems - Delivery Guide

This document describes alert notification routing rules, delivery channel options, and quiet hours constraints.

## 1. Delivery Channels
The system supports multiple notification delivery endpoints:
- **In-App Notifications**: Displayed in the dispatcher dashboard telemetry panel.
- **Email Dispatch**: Sends structured markdown messages detailing the coordinates and risk assessment report.
- **SMS / Push**: Staged for high-importance notification targets (e.g. Critical/High priority alerts).

## 2. Quiet Hours & Suppressions
Dispatcher fatigue is a serious concern. The notification system supports quiet hour blocks configured individually per channel:
- **Time Formatting**: Quiet hours are stored in `HH:MM` format (e.g. `22:00` start, `06:00` end).
- **Midnight-Crossing Support**: Handled automatically (e.g. 22:00 to 06:00 correctly suppresses dispatches overnight).
- **Graceful Hold**: Notifications created during quiet hours are marked `pending` with `Quiet hours active` info logs. These can be flushed during working hours.
