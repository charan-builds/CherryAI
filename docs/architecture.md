# Cherry AI Architecture

## Goals

Cherry AI starts as a local-first Windows desktop assistant and should grow into an agentic system without needing a structural rewrite. The foundation separates UI, configuration, persistence, and backend engines so each capability can evolve independently.

## Runtime Flow

1. `main.py` loads settings from environment variables and `.env`.
2. Logging is configured with console output and a rotating file under `logs/`.
3. SQLite is initialized through SQLAlchemy under the configured data directory.
4. The PyQt frontend starts and receives a composed backend `ServiceRegistry`.

## Layers

### Frontend

`frontend/` owns the PyQt desktop shell, widgets, styles, dashboard pages, notifications, and assets. `frontend/windows/main_window.py` composes reusable widgets and pages; individual controls live under `frontend/widgets/`, and QSS themes live under `frontend/styles/`. UI code should call backend services through the service registry instead of importing engine internals directly.

### Backend

`backend/` is split by capability:

- `ai_engine`: local model access through Ollama
- `ollama_service`: local Ollama connectivity, retries, timeout handling
- `prompt_manager`: reusable prompt templates stored outside business logic
- `intent_parser`: structured JSON-style intent extraction and fallback parsing
- `action_router`: maps AI intents to backend services
- `ai_response_handler`: natural-language response formatting
- `chat_session_manager`: persisted chat session interaction history
- `planner_engine`: goal decomposition and plan creation
- `automation_engine`: safe structured desktop automation tools
- `automation_engine/automation_manager`: permission -> execute -> history pipeline
- `automation_engine/tool_registry`: structured automation tool definitions
- `automation_engine/permission_manager`: safe, medium, and high-risk policy
- `automation_engine/app_launcher`: Windows app launching
- `automation_engine/browser_automation`: websites, YouTube, playlists, study resources
- `automation_engine/screenshot_service`: timestamped screenshots
- `automation_engine/action_history_manager`: persisted action audit history
- `observer_engine`: local state and context gathering
- `analytics_engine`: local product and health events
- `memory_engine`: memory storage and retrieval boundary
- `notification_engine`: user-facing notifications
- `task_engine`: task creation and orchestration

`backend/service_registry.py` is the composition root for these services.

The task engine is now backed by SQLite through a repository layer. The service owns validation, CRUD, completion workflow, filters, daily summaries, logging, and placeholder analytics events.

The observer engine is split into active-window, idle, focus, study-session, event-bus, and state-manager modules. It persists activity logs, study sessions, and observer events while exposing a small polling API for the desktop UI.

The automation engine exposes structured tools through a registry and routes all execution through permission checks and action history persistence. AI code requests actions through intents; it never launches apps or manipulates the desktop directly.

The AI runtime follows an intent-routing pattern: the AI extracts intent, the action router calls backend services, and the response handler formats the final conversational reply. UI and database logic stay outside direct model control.

### Database

`database/` owns SQLAlchemy setup. `init_db.py` creates the schema and seeds a metadata record. The task model lives in `database/task_models.py`, AI chat history lives in `database/ai_models.py`, observer data lives in `database/observer_models.py`, and automation action history lives in `database/automation_models.py`. Future durable entities should be added as ORM models and then migrated through Alembic when schema evolution begins.

### Configuration

`config/settings.py` loads typed settings from `.env` and process environment variables. The rest of the app depends on `AppSettings`, not raw `os.environ` calls.

### Utilities

`utils/` contains cross-cutting helpers such as path resolution and logging setup. Keep this folder small; domain logic belongs in backend engines.

## Design Principles

- Local-first by default.
- Environment variables define deployment boundaries.
- `pathlib` is used for filesystem paths.
- Engines expose stable interfaces so future agents can coordinate capabilities safely.
- Heavy integrations are imported lazily when startup should remain lightweight.
- Docker compatibility is preserved by separating GUI startup from `--no-gui` health checks.

## Next Engineering Steps

- Add Alembic migrations once persistent domain models are introduced.
- Move memory and task placeholders from in-memory stores to SQLite tables.
- Add an async job runner for long model calls and desktop automation.
- Add a permissions layer before agent-driven automation.
- Add integration tests for Ollama and PyAutoGUI behind opt-in markers.
