# Frontend Architecture

The Cherry AI frontend is a PyQt6 desktop shell built from small reusable widgets. The main window composes the application layout and coordinates navigation, while pages and components remain independent.

## Structure

```text
frontend/
├── app.py                       # QApplication setup and theme loading
├── assets/                      # Future icons, images, packaged UI assets
├── dashboard/                   # Dashboard and assistant workspace pages
├── notifications/               # Notification coordination
├── styles/                      # QSS themes and stylesheet loader
├── widgets/                     # Reusable UI components
└── windows/                     # Main application windows
```

## Main Window

`frontend/windows/main_window.py` is the composition root for the desktop UI. It owns:

- sidebar navigation switching
- top bar status updates
- stacked page routing
- footer status messages
- placeholder assistant interactions

It does not define low-level widget styling or message rendering.

## Reusable Widgets

- `SidebarNavigation`: navigation rail with Dashboard, Tasks, Study Mode, Memory, Analytics, and Settings.
- `TopBar`: section title, subtitle, and startup/loading status indicator.
- `ChatDisplayArea`: assistant panel containing the response history.
- `ScrollableResponsePanel`: message bubble list with loading placeholder support.
- `CommandInputArea`: command text field and send button.
- `StatusFooter`: compact footer/status area.
- `PlaceholderPage`: reusable shell for future modules.
- `TaskFormWidget`, `TaskFilterBar`, `TaskSummaryWidget`, and `TaskCard`: reusable task management components.

## Tasks Page

`frontend/tasks/tasks_page.py` replaces the original Tasks placeholder with a functional productivity workspace. It loads persisted tasks on startup, creates tasks, renders task cards, handles completion and reopening, supports status/priority filtering, and refreshes statistics dynamically.

## Dashboard AI Chat

`frontend/dashboard/chat_worker.py` runs dashboard messages on a background `QThread`. This prevents Ollama requests, intent parsing, routing, and response persistence from blocking the PyQt UI thread. The dashboard shows a loading/typing indicator while the worker is active.

## Study Mode

`frontend/study/study_page.py` integrates with the observer engine. It supports starting and stopping study sessions, displays current active app/window, and renders live focus, idle, app-switch, and distraction metrics. The main window updates it through a lightweight `QTimer`.

Study Mode also exposes automation quick actions. `frontend/study/automation_worker.py` runs tool execution in a background `QThread`, and the page prompts for confirmation when the automation engine returns a medium-risk decision.

## Theme System

`frontend/styles/theme.py` loads QSS files by theme name. The default `dark_theme.qss` gives the interface a modern dark appearance while keeping style concerns out of widget classes.

## Future Compatibility

The current notification center is intentionally small, but it provides a clean route for future toast notifications, a system tray integration, or a floating assistant widget. The response panel already exposes loading methods so model streaming can replace placeholder responses without changing the page layout.
