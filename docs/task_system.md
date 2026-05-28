# Task Management System

Cherry AI now includes a SQLite-backed task management system. It is the first functional productivity workflow in the app and follows the same modular structure as the rest of the project.

## Backend Flow

```text
PyQt TasksPage
    -> backend.task_engine.service.TaskEngine
    -> backend.task_engine.repository.TaskRepository
    -> database.task_models.Task
    -> SQLite
```

## Database Model

`database/task_models.py` defines the `Task` ORM model with:

- `id`
- `title`
- `description`
- `status`
- `priority`
- `created_at`
- `completed_at`

`database/init_db.py` imports the model before `Base.metadata.create_all(...)`, so the `tasks` table is created during normal startup.

## Service Layer

`backend/task_engine/service.py` owns validation, task CRUD, completion workflow, filters, statistics, daily summaries, logging, and placeholder analytics events.

`backend/task_engine/repository.py` owns database access. It converts ORM rows into immutable `TaskRecord` objects before returning them to the rest of the app.

## Frontend

`frontend/tasks/tasks_page.py` integrates task management into the existing sidebar route. Reusable widgets live in `frontend/widgets/`:

- `TaskFormWidget`
- `TaskFilterBar`
- `TaskSummaryWidget`
- `TaskCard`

The page loads persisted tasks on startup, supports creation, filtering, completion/reopen, deletion, dynamic refresh, and summary updates.

## Testing

Task coverage includes CRUD, persistence across service instances, filtering, statistics, daily summary generation, and a PyQt widget smoke test.
