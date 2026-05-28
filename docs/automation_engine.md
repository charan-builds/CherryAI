# Automation Engine

Cherry AI now includes a safe local automation foundation. The engine exposes structured tools, checks permissions before execution, and persists every action for auditability.

## Modules

```text
backend/automation_engine/
├── automation_manager/       # permission -> execute -> history pipeline
├── tool_registry/            # structured tool definitions
├── permission_manager/       # safety decisions
├── app_launcher/             # configured Windows app launching
├── browser_automation/       # URLs, YouTube, playlists, study resources
├── screenshot_service/       # timestamped screenshots
└── action_history_manager/   # persisted action history
```

## Tools

- `open_app`
- `open_website`
- `play_music`
- `take_screenshot`
- `open_study_workspace`

Each tool defines an input schema, safety level, and execution handler.

## Safety Model

- `safe`: auto-allowed, such as opening VS Code or a website.
- `medium`: requires confirmation, such as screenshots or a multi-step study workspace.
- `high`: blocked.

The permission manager also blocks unsafe text patterns such as shutdown, registry edits, shell commands, and file deletion requests.

## Persistence

`database/automation_models.py` stores:

- `AutomationActionLog`
- `ToolExecutionLog`
- `PermissionDecisionLog`

These records include parameters, permission status, success/failure, errors, timestamps, and duration.

## AI Integration

Automation intents are routed through `ActionRouter`, not directly through UI or model code. Supported automation intents:

- `open_app`
- `open_website`
- `play_music`
- `take_screenshot`
- `start_study_workspace`

## Frontend Integration

Study Mode includes quick actions for opening a study workspace, playing focus music, and taking screenshots. Automation runs in a `QThread`, and medium-risk actions trigger a confirmation prompt.
