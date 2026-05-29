# Cherry AI v1 Readiness Audit

Audit date: 2026-05-29

Scope: current Cherry AI repository, including the local-first desktop shell, backend engines, SQLite persistence, memory, workflow automation, knowledge intelligence, and Personal OS layer.

## Executive Verdict

Cherry AI is not yet ready to be called a stable v1 product.

It is ready for internal alpha or early beta usage because the architecture is coherent, the services are modular, persistence is broad, and the automated suite is currently green. It should not add ML, Voice, or Multi-Agent systems until the critical and high-priority items below are addressed.

The main readiness blockers are schema governance, data integrity, privacy controls, true crash/session recovery, large composition modules, and performance risks from synchronous multi-query runtime paths.

Current evidence:

- Python files audited: 305
- Python lines: about 22,674 total, about 19,147 non-comment/non-blank
- Largest modules:
  - `frontend/windows/main_window.py`: 716 lines
  - `backend/workflow_state_manager/repository.py`: 425 lines
  - `frontend/knowledge/knowledge_center_page.py`: 398 lines
  - `backend/operating_context_manager/repository.py`: 396 lines
  - `backend/service_registry.py`: 375 lines
  - `frontend/workspace/workspace_center.py`: 356 lines
  - `backend/workflow_execution_engine/service.py`: 351 lines
- Tables: 28 including `app_metadata`
- Explicit database foreign keys: 0
- Current test suite: 79 tests passing with `pytest --basetemp .pytest_tmp_run -p no:cacheprovider`

## Readiness Summary

| Area | Readiness | Summary |
|---|---:|---|
| Architecture | Medium | Strong local-first layering, but composition is becoming centralized and heavy. |
| Module Boundaries | Medium | Most domains are well separated, but frontend, registry, and Personal OS orchestration cross many boundaries. |
| Dependency Graph | Medium | No obvious package-level mutual cycles detected, but fan-out is high in `service_registry` and `main_window`. |
| Database Design | Medium-Low | Broad persistence exists, but lacks migrations, foreign keys, cascades, and several compound/date indexes. |
| Memory System | Medium | Good layered design, but retrieval is heuristic and sync, with weak privacy and retention controls. |
| Workflow Engine | Medium | Solid deterministic execution model, but restart recovery is not complete enough for v1. |
| Automation Layer | Medium-Low | Safety pipeline exists, but policy is shallow for a consumer-grade assistant. |
| Knowledge Layer | Medium | Useful deterministic summaries, code and screen analysis, but no robust extraction or semantic index. |
| Personal OS Layer | Medium-Low | Directionally strong, but too new and only partially restores actual working environments. |
| Performance | Medium-Low | Fine for small local datasets, risky as logs, memories, snapshots, and recommendations grow. |
| Security | Low-Medium | Local-first is good, but sensitive data is stored unencrypted and automation policy needs hardening. |
| Test Coverage | Medium | Good breadth for unit/smoke tests, limited integration, crash recovery, security, and performance coverage. |
| Maintainability | Medium | Consistent patterns, but duplication and large orchestration modules are accumulating. |
| Scalability | Low-Medium | Personal SQLite design is acceptable, but not ready for multi-agent or high-volume event/data workloads. |

## Strengths

- Clear local-first direction with PyQt UI, backend services, repositories, and typed settings.
- Strong domain naming: task, workflow, observer, memory, knowledge, automation, recommendation, and Personal OS layers are easy to locate.
- Consistent service/repository/dataclass patterns make most modules approachable.
- Deterministic fallbacks exist for LLM, OCR, PDF, intent parsing, and summaries, which helps testability.
- Automation execution has permission checks, sandbox rate limiting, action history, and event publication.
- Workflow engine supports validation, persisted state, retries, pause, resume, cancel, history, and reflection.
- Memory system has working memory, semantic memory, retrieval, scoring, prompt injection, and consolidation.
- Knowledge layer now covers documents, code, screenshots, notes, and semantic memory linking.
- Personal OS layer adds workspace profiles, context switching, snapshots, session recovery, and resume answers.
- Test suite is broad enough to catch many regressions before v1 stabilization.

## Weaknesses

- `backend/service_registry.py` is a large composition root with about 47 package-level outgoing dependencies.
- `frontend/windows/main_window.py` mixes shell wiring, workflow control, observer polling, Personal OS refresh, notifications, companion refresh, and platform refresh.
- Database schema is created with `Base.metadata.create_all` and no migration baseline is active.
- SQLAlchemy models use string IDs for cross-table references but no `ForeignKey`, relationship, cascade, or referential integrity constraints.
- Several repositories create their own engine/session factory, which makes shared transactions, instrumentation, and connection tuning harder.
- Many count and date-window queries load full ORM rows and count in Python.
- Frontend imports backend DTOs and services directly across many widgets/pages, which increases UI/domain coupling.
- The Personal OS and older workspace preparation layer overlap: `workspace_preparation_engine` launches workflow definitions while `workspace_profile_manager` owns operating profiles.
- Some important runtime mechanisms are in memory only: event bus history, lifecycle state, running workflow controls, chat session IDs, and analytics placeholders.
- Security controls are helpful but not yet product-grade for automation, document ingestion, or sensitive local memory.

## Critical Issues

### 1. No Schema Migration or Data Integrity Plan

The project depends on Alembic but currently initializes with `Base.metadata.create_all`. That is acceptable for prototypes, but not for v1 user data. Once users have local databases, schema changes need reversible migrations, compatibility checks, and a backup/restore path.

Impact:

- Future releases can silently create drift between expected and actual schema.
- Data repair becomes manual.
- Rollbacks are unsafe.
- ML, voice, or multi-agent additions will multiply schema churn.

Required v1 gate:

- Add an Alembic baseline migration for the current schema.
- Add migration tests against an empty DB and an upgraded previous DB.
- Store and enforce schema version beyond the current metadata seed.
- Add local DB backup before migration.

### 2. No Database Foreign Keys or Relationship Constraints

The audit found zero explicit foreign keys. Tables such as workflow steps, workflow history, tool execution logs, knowledge semantic links, activity snapshots, and saved contexts all store related IDs as plain strings.

Impact:

- Orphaned workflow steps, logs, memory links, and operating snapshots can accumulate.
- Deletes and data repairs are unsafe.
- Resume and recovery features can reference missing workflows, study sessions, or memories.

Required v1 gate:

- Add foreign keys for direct ownership relationships:
  - `workflow_steps.workflow_id -> workflows.id`
  - `workflow_history.workflow_id -> workflows.id`
  - `workflow_execution_logs.workflow_id -> workflows.id`
  - `tool_execution_logs.action_id -> automation_action_logs.id`
  - `knowledge_memories.semantic_memory_id -> semantic_memories.id` when non-empty, or move to nullable FK
  - operating context active IDs where lifecycle ownership is clear
- Add cascade rules where data is owned.
- Add cleanup routines for intentionally loose references.

### 3. Session Recovery Is Not Yet True Product Recovery

The Personal OS layer can restore saved operating metadata and summarize active/pending state, but it does not yet guarantee full restoration of actual work after process restart.

Current gaps:

- Running workflow controls are in memory.
- Executable workflow plans are not restored into an execution queue from persisted state.
- Workspace switching updates context and can pause workflows, but does not reliably reopen all apps, documents, URLs, and study surfaces from profiles.
- Snapshots are taken on UI timer cadence, so headless/background state may not be captured.

Required v1 gate:

- Persist executable workflow plans and provide a restart-safe workflow rehydration path.
- Add a recovery queue that can reopen workspace apps/docs/URLs from profile state.
- Make snapshots service-level, not only UI-timer-driven.
- Add crash recovery tests that simulate process restart.

### 4. Sensitive Local Data Is Stored Without a Privacy Model

Cherry stores prompts, AI responses, task data, memories, document summaries, screenshots/OCR text, automation parameters, observer events, and workspace snapshots in local SQLite/log files.

Impact:

- User data is readable by any local process/account with file access.
- Automation logs can contain URLs, file paths, and possibly secrets.
- Future voice or multi-agent capabilities will add more sensitive data.

Required v1 gate:

- Define a privacy model before adding voice, ML, or multi-agent features.
- Add local data export/delete controls.
- Add sensitive-field redaction for logs and persisted automation parameters.
- Add optional database encryption or OS-protected storage.
- Add retention policies for events, screenshots, OCR, snapshots, and prompts.

## High Priority Improvements

### Database Indexes and Query Shape

Add missing indexes and replace Python-side counting/filtering with SQL aggregates.

Recommended indexes:

- `tasks(created_at)`
- `tasks(completed_at)`
- `tasks(status, priority, created_at)`
- `ai_interactions(session_id, created_at)`
- `ai_interactions(created_at)`
- `activity_logs(started_at)`
- `activity_logs(application_name, started_at)`
- `study_sessions(status, started_at)`
- `study_sessions(started_at)`
- `study_sessions(ended_at)`
- `observer_events(event_type, created_at)`
- `observer_events(created_at)`
- `workflow_steps(workflow_id, position)`
- `workflow_steps(workflow_id, step_key)` with uniqueness
- `workflow_history(workflow_id, created_at)`
- `workflow_history(created_at)`
- `workflow_execution_logs(workflow_id, created_at)`
- `scheduled_workflows(status, next_run_at)`
- `semantic_memories(category, last_reinforced_at)`
- `semantic_memories(source_type, source_id)` with uniqueness when `source_id` is present
- `semantic_memories(category, title)` for reinforcement lookup
- `working_memory_states(expires_at)`
- `working_memory_states(state_type, updated_at)`
- `recommendation_logs(cooldown_key, created_at)`
- `recommendation_logs(status, delivered_at)`
- `daily_timeline_entries(entry_date, started_at)`
- `automation_action_logs(started_at)`
- `automation_action_logs(tool_name, started_at)`
- `permission_decision_logs(created_at)`
- `tool_execution_logs(action_id, created_at)`
- `saved_operating_contexts(updated_at)`
- `activity_snapshots(current_workspace, created_at)`
- `workspace_profiles(profile_type, is_active)`

Query refactors:

- Replace `len(session.scalars(select(...)).all())` with SQL `count`.
- Replace `TaskRepository.list_created_on` and `list_completed_on` Python filtering with date-window SQL.
- Add aggregate queries for productivity metrics.
- Add pagination to history/snapshot/list endpoints.

### Split Large Composition Modules

`MainWindow` and `ServiceRegistry` are the two biggest maintainability pressure points.

Recommended refactors:

- Split `ServiceRegistry` into builders:
  - core runtime
  - memory and knowledge
  - workflow and automation
  - companion and Personal OS
  - frontend-facing registry
- Split `MainWindow` into controllers:
  - chat controller
  - workflow controller
  - observer controller
  - companion refresh controller
  - Personal OS controller
  - diagnostics controller
- Keep the PyQt shell focused on layout and page navigation.

### Harden Automation Policy

Current automation policy blocks keyword patterns and requires confirmation for medium-risk tools. This is a good start but not enough for stable v1.

Required improvements:

- Use structured allowlists for apps, URL schemes, domains, and file paths.
- Redact automation parameters before persistence/logging.
- Add explicit user confirmation UI for all medium-risk actions.
- Add policy tests for nested parameters, URL edge cases, file paths, shell-like payloads, and prompt-injection attempts.
- Add per-tool capability manifests and scopes.

### Make Background Work Explicit

Cherry currently uses PyQt workers, sync service calls, and synchronous event bus delivery. This is acceptable for small workloads but risky as knowledge indexing, workflow recovery, and future voice or agents arrive.

Recommended changes:

- Add a local job queue abstraction for long-running tasks.
- Give jobs durable IDs, status, cancellation, retry policy, and progress.
- Move workflow execution, document analysis, OCR, and memory consolidation onto this queue.
- Persist queue state for crash recovery.

### Improve Test Coverage Around Product Risks

Add tests that cover actual v1 risk rather than only happy-path service behavior.

High-value missing tests:

- Migration tests.
- Restart recovery tests for workflows, snapshots, and workspaces.
- DB integrity tests with foreign key enforcement.
- Automation security tests.
- Performance tests with large local databases.
- UI smoke tests for Workspace Center, recovery dialog, and context switching.
- Real optional integration tests behind markers for Ollama, PyAutoGUI, PDF extraction, OCR, and browser opening.

## Medium Priority Improvements

### Memory System

Strengths:

- Clear split between working memory, semantic memory, retrieval, injection, scoring, and consolidation.
- TTL-based working memory and semantic memory pruning exist.
- Context retrieval composes tasks, study state, summaries, patterns, semantic memory, and chat history.

Risks:

- Retrieval is heuristic and not vector/embedding based.
- Context retrieval does several synchronous DB queries per AI request.
- Memory can mix temporary context, user preference, task state, and behavioral inference without strong provenance controls.
- Privacy controls and memory deletion UX are not yet visible.

Improvements:

- Add source/provenance controls and user-facing memory deletion.
- Add memory confidence decay and retention policies by category.
- Add optional local embeddings/vector index after v1 stabilization, not before.
- Add prompt-injection isolation for document/screen-derived memory.

### Workflow Engine

Strengths:

- Strong deterministic execution core.
- Clear workflow/step schemas.
- Pause, resume, cancel, retries, validation, history, event publication, and reflection are in place.

Risks:

- Execution controls are in memory.
- Workflow plan rehydration after restart is incomplete.
- Step progress increments are approximate.
- Long-running step timeout uses threads, but action cancellation may not stop external side effects.
- Dependencies are sequential only, which is safe but limits future scalability.

Improvements:

- Persist serialized workflow plans with each workflow.
- Add a `resume_persisted_workflow(workflow_id)` service.
- Make running/paused/cancelled semantics restart-safe.
- Add explicit compensating-action design for partially completed automation.
- Add workflow versioning before multi-agent planning.

### Knowledge Layer

Strengths:

- Document, code, and screen intelligence are deterministic and testable.
- Knowledge memories link into semantic memory.
- Project summarization has a file limit and skips common heavy directories.

Risks:

- Optional dependencies `pypdf`, `PIL`, and `pytesseract` are not in `requirements.txt`.
- PDF fallback extraction is basic.
- OCR is optional and silent when unavailable.
- No incremental file index or watcher.
- Knowledge dedupe hash uses summary content rather than stable source content metadata.

Improvements:

- Add optional extras or documented install profiles for PDF/OCR.
- Add source file metadata: path, mtime, size, content hash.
- Add incremental indexing and re-index invalidation.
- Add source trust levels and prompt-injection treatment for external documents.

### Personal OS Layer

Strengths:

- Provides the right product direction: workspace profiles, context state, saved contexts, snapshots, recovery, and resume summaries.
- Has dedicated tests for workspace profiles, snapshots, switching, recovery, and resume.

Risks:

- New layer duplicates concepts with `workspace_preparation_engine`.
- Recovery currently restores state more than the actual desktop environment.
- Snapshot retention and pruning are absent.
- Saved contexts reference workflow/study/task IDs without referential integrity.
- UI refresh and snapshot timing are tied to the running desktop shell.

Improvements:

- Merge workspace profiles and workspace preparation into one workspace model.
- Add workspace activation plans that can reopen apps, docs, URLs, and study mode.
- Add snapshot retention and compaction.
- Add service-level background snapshot scheduler.
- Add crash/restart recovery tests.

### Documentation

`docs/architecture.md` is now stale. It omits newer systems such as Personal OS, knowledge intelligence, workflow state, startup briefings, context retrieval, and the expanded memory system.

Improvements:

- Update architecture docs after the v1 refactors.
- Add diagrams for dependency graph, DB model ownership, and runtime event flow.
- Add a security/privacy document.
- Add an operational troubleshooting guide.

## Nice-to-Have Improvements

- Add import graph validation to CI to prevent future package cycles.
- Add `ruff`, `mypy` or `pyright`, and formatting checks.
- Add benchmark scripts for startup, context retrieval, workflow execution, document analysis, and UI refresh.
- Add a repository base class or session provider to reduce repeated boilerplate.
- Add table naming/index naming conventions for Alembic.
- Add UI accessibility checks for text contrast, keyboard navigation, and high-DPI layouts.
- Add a plugin/capability manifest system after v1 stabilization.
- Add typed event payload schemas for high-value event categories.
- Add a local diagnostics page section for DB size, snapshot count, memory count, and retention status.

## Performance Bottlenecks

- AI request handling can synchronously update memory, retrieve context, parse intent, route actions, and persist chat records.
- Context retrieval performs multiple DB reads and scores all candidates in Python.
- Productivity analysis and task summaries load rows and count in Python.
- Event bus delivery is synchronous and subscriber failures are caught but still run inline.
- `MainWindow` refresh loops can call companion, diagnostics, Personal OS, observer, and workflow refresh paths close together.
- Workflow execution is sequential and uses thread timeouts for steps.
- Large QLabels are used for multi-line UI summaries, which may become inefficient for long histories.
- Each repository builds its own engine/session factory from settings, making connection pooling and instrumentation fragmented.

## Security Risks

- SQLite stores sensitive prompts, responses, memories, summaries, snapshots, and automation parameters without encryption.
- Logs can expose local paths, model prompts, URLs, app names, and errors.
- Document and screen intelligence can ingest untrusted content into memory without a trust boundary.
- Automation can open apps and URLs with limited structured allowlisting.
- There is no user-visible data deletion/export center yet.
- There is no tamper-evident audit trail for automation or memory changes.
- No threat model exists for future multi-agent execution.

## Scalability Concerns Before ML, Voice, or Multi-Agent

Do not add ML, Voice, or Multi-Agent systems until these are resolved:

- Durable job queue and restart-safe execution.
- Migration and DB integrity baseline.
- Privacy controls and retention.
- Clear ownership between Personal OS, workflow, workspace, memory, and automation systems.
- Event bus strategy for high-volume events.
- Semantic retrieval/index strategy for larger knowledge and memory stores.
- Agent capability and permission model.
- Performance tests with realistic local data volume.

## Refactoring Opportunities

1. Create a `DatabaseRuntime` or `PersistenceContext` that owns engine/session factory and exposes repositories.
2. Split `ServiceRegistry` into domain builders and a thinner final registry.
3. Split `MainWindow` into controllers and keep UI composition declarative.
4. Merge workspace profile and workspace preparation models.
5. Introduce durable job/workflow runner as a separate runtime subsystem.
6. Move repeated JSON serialization helpers into a shared database utility.
7. Add typed event payloads or event factories for high-value categories.
8. Add repository-level pagination and aggregate methods.
9. Add privacy/redaction helpers used by logs, automation, memory, and knowledge ingestion.
10. Update docs to reflect actual module map and v1 boundaries.

## Technical Debt Register

| Debt | Severity | Why It Matters |
|---|---:|---|
| No Alembic baseline | Critical | User data cannot be safely upgraded. |
| No foreign keys | Critical | Recovery and history can reference deleted/missing rows. |
| In-memory workflow controls | Critical | Process restart breaks true resume semantics. |
| Unencrypted sensitive local data | Critical | Product trust risk. |
| Large `MainWindow` | High | UI behavior becomes hard to reason about. |
| Large `ServiceRegistry` | High | Dependency graph becomes fragile as systems grow. |
| Repeated DB engine/session creation | High | Hard to tune, observe, and transact. |
| Python-side counts/date filters | High | Performance degrades with normal usage history. |
| Basic automation keyword policy | High | Insufficient for stable user-facing automation. |
| Stale architecture docs | Medium | Contributors will misunderstand system boundaries. |
| Optional OCR/PDF dependencies implicit | Medium | Knowledge features can silently degrade. |
| Workspace model duplication | Medium | Context switching and workspace launch can diverge. |
| Minimal analytics persistence | Medium | Product health and usage insights are limited. |

## Priority Roadmap

### Critical Issues

1. Add Alembic migration baseline and schema upgrade tests.
2. Add database foreign keys, cascades, cleanup routines, and integrity tests.
3. Make workflow/session recovery restart-safe with persisted executable plans and job state.
4. Add privacy model: encryption option, redaction, retention, export, and deletion.

### High Priority Improvements

1. Add missing indexes and SQL aggregate queries.
2. Split `ServiceRegistry` and `MainWindow`.
3. Introduce durable background job queue.
4. Harden automation allowlists, confirmation, and parameter redaction.
5. Add v1 risk tests: migration, crash recovery, security, performance, and UI smoke.
6. Merge workspace profile and workspace preparation concepts.

### Medium Priority Improvements

1. Update architecture and security docs.
2. Improve memory provenance, deletion, and retention.
3. Improve knowledge indexing, extraction, and source metadata.
4. Add event payload typing and better event-bus observability.
5. Add pagination and retention controls to logs, snapshots, memories, and recommendations.
6. Add optional extras for PDF/OCR dependencies.

### Nice-to-Have Improvements

1. Add import graph checks.
2. Add static typing and linting in CI.
3. Add performance benchmark scripts.
4. Add accessibility checks for PyQt UI.
5. Add plugin/capability manifests after v1 stabilization.
6. Add tamper-evident audit hashes for automation logs.

## V1 Go/No-Go Checklist

Cherry AI should be considered v1-ready only when all of these are true:

- Database migrations are active and tested.
- Referential integrity is enforced or intentionally documented for each relationship.
- A user can upgrade from an older local DB without data loss.
- A user can recover after process restart and see accurate active/pending work.
- Automation actions have scoped allowlists, confirmation, logs, and redaction.
- Sensitive local data has export/delete/retention controls.
- Main runtime modules are split enough that adding features does not require editing huge orchestration files.
- Performance is measured against realistic local data volumes.
- Test suite includes crash recovery, security, migration, and UI smoke coverage.
- Architecture/security docs match the actual code.

## Final Recommendation

Freeze expansion into ML, Voice, and Multi-Agent systems until the Critical Issues and at least the first five High Priority Improvements are complete.

Cherry has a solid foundation and the right product instincts. The current codebase is best treated as a strong v0.8 to v0.9 foundation: feature-rich, internally usable, and ready for hardening, but not yet stable enough for v1 users who expect durable data, reliable recovery, privacy guarantees, and predictable automation safety.
