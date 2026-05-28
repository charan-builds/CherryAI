# Observer Engine

Cherry AI now includes a safe local observer engine for behavioral intelligence. It tracks active windows, idle state, focus behavior, distractions, and study sessions without letting AI code directly control the UI or database.

## Modules

```text
backend/observer_engine/
├── active_window_tracker/      # active app/window title snapshots
├── idle_detector/              # keyboard/mouse inactivity
├── focus_tracker/              # app switches, focus time, distractions
├── study_session_manager/      # study session lifecycle
├── observer_event_bus/         # reusable observer events
└── observer_state_manager/     # persistence and current state
```

## Events

Supported observer events:

- `app_changed`
- `idle_detected`
- `focus_lost`
- `study_started`
- `study_completed`
- `distraction_detected`

Events are emitted through `ObserverEventBus` and persisted as `observer_events`.

## Persistence

`database/observer_models.py` defines:

- `ActivityLog`: active app/window usage intervals with duration
- `StudySession`: study topic, timing, focus, idle, and interruption statistics
- `ObserverEventLog`: durable observer event history

## Frontend

Study Mode uses the observer engine for live session status, a focus timer, current active app/window display, idle time, app-switch count, and distraction count. The main window polls observer state with a `QTimer`, keeping the UI responsive.

## Configuration

Environment variables:

- `CHERRY_OBSERVER_ENABLED`
- `CHERRY_OBSERVER_POLL_INTERVAL_SECONDS`
- `CHERRY_IDLE_THRESHOLD_SECONDS`
- `CHERRY_DISTRACTION_KEYWORDS`
