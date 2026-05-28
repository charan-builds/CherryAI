# AI Runtime Architecture

Cherry AI now has a modular local AI runtime that turns dashboard chat into structured backend actions.

## Flow

```text
Dashboard chat
    -> ChatWorker QThread
    -> AIEngine
    -> IntentParser
    -> ActionRouter
    -> TaskEngine or no-op backend action
    -> AIResponseHandler
    -> ChatSessionManager
    -> SQLite ai_interactions
```

The AI never manipulates UI widgets or database tables directly. It extracts intent, the router maps intent to backend services, services execute work, and the response handler formats a conversational answer.

## Modules

- `backend/ollama_service`: local Ollama connectivity, timeout settings, retries, supported model checks, sync and async-ready generation.
- `backend/prompt_manager`: reusable prompt templates stored on disk.
- `backend/intent_parser`: JSON-style intent extraction with validation and fallback heuristics.
- `backend/action_router`: maps intents to backend services.
- `backend/ai_response_handler`: formats final responses and uses graceful fallbacks when Ollama is unavailable.
- `backend/chat_session_manager`: creates chat sessions and persists interaction history.

## Supported Intents

- `create_task`
- `list_tasks`
- `summarize_tasks`
- `motivational_response`
- `general_chat`

## Persistence

`database/ai_models.py` stores:

- user prompt
- AI response
- detected intent
- session id
- timestamp

## Frontend Runtime

`frontend/dashboard/chat_worker.py` runs the AI workflow on a `QThread`, keeping the PyQt UI responsive while Ollama or routing work runs in the background.
