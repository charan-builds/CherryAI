# Cherry AI

Cherry AI is a local-first desktop AI assistant foundation for Windows-native development. The initial stack is Python, PyQt6, Ollama, SQLite, SQLAlchemy, and PyAutoGUI.

## Quick Start

```powershell
cd "C:\Cherry AI"
.\scripts\setup_venv.ps1
.\scripts\run.ps1
```

If pip cannot verify PyPI certificates on your Windows machine, use the explicit trusted-host fallback:

```powershell
.\scripts\setup_venv.ps1 -TrustPypiHost
```

Run a startup check without opening the desktop window:

```powershell
.\scripts\run.ps1 -NoGui
```

If PowerShell script execution is disabled, use:

```powershell
.\.venv\Scripts\python.exe main.py --no-gui
```

## Project Structure

```text
Cherry AI/
├── backend/                 # Agentic engines and orchestration services
│   ├── ai_engine/           # Ollama/local model access
│   ├── ollama_service/      # Ollama connectivity, retries, timeout handling
│   ├── prompt_manager/      # Reusable prompt templates
│   ├── intent_parser/       # Structured intent extraction
│   ├── action_router/       # Intent-to-service routing
│   ├── ai_response_handler/ # Conversational response formatting
│   ├── chat_session_manager/# Persisted AI interaction history
│   ├── planner_engine/      # Goal decomposition and planning
│   ├── automation_engine/   # PyAutoGUI desktop automation
│   ├── observer_engine/     # Local context and system observation
│   ├── analytics_engine/    # Local-first usage and health events
│   ├── memory_engine/       # Assistant memory interfaces
│   ├── notification_engine/ # User-facing notifications
│   └── task_engine/         # Durable task orchestration
├── config/                  # Environment-driven settings
├── database/                # SQLAlchemy models, sessions, initialization
├── docs/                    # Architecture and engineering notes
├── frontend/                # PyQt6 desktop UI
│   ├── windows/             # Main application windows
│   ├── widgets/             # Reusable controls and panels
│   ├── styles/              # Theme-ready QSS stylesheets
│   ├── dashboard/           # Assistant workspace pages
│   ├── tasks/               # Task management page
│   ├── study/               # Study Mode and observer status page
│   ├── notifications/       # UI notification coordination
│   └── assets/              # Future frontend assets
├── logs/                    # Runtime logs
├── scripts/                 # Windows PowerShell developer scripts
├── tests/                   # Pytest test suite
├── utils/                   # Shared helpers
├── main.py                  # Application entry point
├── requirements.txt
└── .env.example
```

## Configuration

Copy `.env.example` to `.env` for local overrides. Cherry AI uses environment variables for paths, logging, Ollama settings, and desktop automation safety.

Important defaults:

- Runtime data: `.cherry_data/`
- SQLite database: `.cherry_data/cherry_ai.db`
- Logs: `logs/cherry_ai.log`
- SQL echo logging: disabled unless `CHERRY_SQL_ECHO=true`
- Ollama host: `http://localhost:11434`
- Ollama model: `llama3.1`
- Ollama timeout: `30` seconds
- Ollama retries: `1`

## Development Commands

```powershell
.\scripts\setup_venv.ps1
.\scripts\run.ps1 -NoGui
.\.venv\Scripts\python.exe -m pytest
```

## Docker Readiness

The project avoids hardcoded OS paths, keeps runtime state outside source modules, and includes `.dockerignore`. The current app is desktop-first; future container work should target headless services, workers, tests, or API layers unless display forwarding is intentionally configured.

## Current Status

The initial app opens a PyQt window, initializes logging, creates the local SQLite database, and composes placeholder backend engines for future agentic workflows.

The frontend now includes a dark themed desktop shell with sidebar navigation, a dashboard chat console, scrollable response panel, command input, startup status indicator, and placeholder responses ready for future Ollama streaming.

The Tasks section is a functional SQLite-backed productivity system with task creation, persisted task cards, completion/reopen workflow, filtering, statistics, and daily summaries.

The Dashboard chat now uses the local AI runtime: Ollama-powered intent extraction with fallback parsing, task routing, natural responses, persistent interaction history, and non-blocking PyQt worker execution.

Study Mode now uses the Observer Engine for active app tracking, idle/focus metrics, distraction detection, study session start/stop, and persisted behavioral events.
