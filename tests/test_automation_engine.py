from backend.action_router.service import ActionRouter
from backend.automation_engine.app_launcher.service import AppLauncher
from backend.automation_engine.browser_automation.service import BrowserAutomation
from backend.automation_engine.permission_manager.service import PermissionManager
from backend.automation_engine.screenshot_service.service import ScreenshotService
from backend.automation_engine.schemas import (
    PERMISSION_BLOCKED,
    PERMISSION_CONFIRMATION_REQUIRED,
    SAFETY_MEDIUM,
    SAFETY_SAFE,
)
from backend.automation_engine.service import AutomationEngine
from backend.intent_parser.schemas import ParsedIntent
from backend.task_engine.service import TaskEngine
from database.init_db import initialize_database
from tests.helpers import make_test_settings


class FakeImage:
    def __init__(self):
        self.saved_path = None

    def save(self, path):
        self.saved_path = path
        path.write_text("fake screenshot", encoding="utf-8")


def build_fake_automation(settings):
    launched = []
    opened_urls = []
    fake_image = FakeImage()
    return (
        AutomationEngine(
            settings=settings,
            app_launcher=AppLauncher(settings, runner=launched.append),
            browser=BrowserAutomation(opener=lambda url: opened_urls.append(url) or True),
            screenshot_service=ScreenshotService(
                settings,
                capture_fn=lambda: fake_image,
            ),
        ),
        launched,
        opened_urls,
        fake_image,
    )


def test_tool_registry_exposes_structured_tools(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    automation, *_ = build_fake_automation(settings)
    tools = {tool.name: tool for tool in automation.list_tools()}

    assert tools["open_app"].safety_level == SAFETY_SAFE
    assert tools["take_screenshot"].safety_level == SAFETY_MEDIUM
    assert "app_name" in tools["open_app"].input_schema["properties"]


def test_permission_manager_blocks_unsafe_parameters(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    automation, *_ = build_fake_automation(settings)
    tool = automation.tool_registry.get("open_app")
    decision = PermissionManager().evaluate(
        tool,
        {"app_name": "shutdown system"},
    )

    assert decision.status == PERMISSION_BLOCKED


def test_safe_open_app_executes_and_persists_history(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    automation, launched, *_ = build_fake_automation(settings)

    result = automation.execute_tool("open_app", {"app_name": "vscode"})
    actions = automation.recent_actions()

    assert result.success is True
    assert launched == [["code"]]
    assert len(actions) == 1
    assert actions[0].tool_name == "open_app"


def test_medium_risk_screenshot_requires_confirmation_then_executes(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    automation, _, _, fake_image = build_fake_automation(settings)

    first = automation.execute_tool("take_screenshot", {})
    second = automation.execute_tool("take_screenshot", {}, confirmed=True)

    assert first.confirmation_required is True
    assert first.permission_status == PERMISSION_CONFIRMATION_REQUIRED
    assert second.success is True
    assert fake_image.saved_path is not None


def test_open_website_and_play_music_use_browser(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    automation, _, opened_urls, _ = build_fake_automation(settings)

    website = automation.execute_tool("open_website", {"url": "example.com"})
    music = automation.execute_tool("play_music", {"query": "lofi focus"})

    assert website.success is True
    assert opened_urls[0] == "https://example.com"
    assert music.success is True
    assert "youtube.com/results" in opened_urls[1]


def test_action_router_routes_automation_intent(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    automation, _, opened_urls, _ = build_fake_automation(settings)
    router = ActionRouter(
        task_engine=TaskEngine(settings=settings),
        automation_engine=automation,
    )

    result = router.route(
        ParsedIntent(intent="open_website", url="https://example.com")
    )

    assert result.success is True
    assert opened_urls == ["https://example.com"]
