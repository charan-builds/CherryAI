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
- `planner_engine`: goal decomposition and plan creation
- `automation_engine`: desktop control through PyAutoGUI
- `observer_engine`: local state and context gathering
- `analytics_engine`: local product and health events
- `memory_engine`: memory storage and retrieval boundary
- `notification_engine`: user-facing notifications
- `task_engine`: task creation and orchestration

`backend/service_registry.py` is the composition root for these services.

The task engine is now backed by SQLite through a repository layer. The service owns validation, CRUD, completion workflow, filters, daily summaries, logging, and placeholder analytics events.

### Database

`database/` owns SQLAlchemy setup. `init_db.py` creates the schema and seeds a metadata record. The task model lives in `database/task_models.py`. Future durable entities should be added as ORM models and then migrated through Alembic when schema evolution begins.

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
