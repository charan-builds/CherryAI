"""Goal planner engine for agentic workflows."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from urllib.parse import quote_plus

from config.settings import AppSettings
from backend.ollama_service.service import OllamaGenerationError, OllamaService
from backend.workflow_state_manager.schemas import (
    ACTION_TYPE_AUTOMATION,
    ACTION_TYPE_NOTIFICATION,
    ACTION_TYPE_NOOP,
    ACTION_TYPE_STUDY_SESSION,
    WorkflowPlan,
    WorkflowStepPlan,
)
from backend.workflow_state_manager.serialization import plan_from_dict

logger = logging.getLogger(__name__)


@dataclass
class GoalPlannerEngine:
    """Converts high-level goals into structured workflow plans."""

    settings: AppSettings
    ollama_service: OllamaService | None = None

    def create_plan(self, goal: str) -> WorkflowPlan:
        """Create a validated-shape plan from a human goal."""
        cleaned_goal = self._clean_goal(goal)
        if self.settings.workflow_ai_planning_enabled and self.ollama_service is not None:
            ai_plan = self._try_ai_plan(cleaned_goal)
            if ai_plan is not None:
                return ai_plan

        return self._heuristic_plan(cleaned_goal)

    def explain_plan(self, plan: WorkflowPlan) -> str:
        """Explain a workflow plan with Ollama when available, else fallback text."""
        fallback = self._fallback_plan_explanation(plan)
        if self.ollama_service is None:
            return fallback

        prompt = (
            "Explain this Cherry AI workflow briefly for a beginner. "
            "Do not add steps.\n\n"
            f"Goal: {plan.goal}\n"
            f"Steps: {[step.name for step in plan.steps]}"
        )
        try:
            return self.ollama_service.generate(prompt)
        except OllamaGenerationError:
            return fallback

    def _heuristic_plan(self, goal: str) -> WorkflowPlan:
        normalized = goal.lower()
        if "study" in normalized or "learn" in normalized:
            return self._study_plan(goal)

        if "music" in normalized:
            return WorkflowPlan(
                goal=goal,
                name="Focus Music Workflow",
                description="Open focus music for the current work session.",
                steps=(
                    WorkflowStepPlan(
                        key="play_focus_music",
                        name="Play focus music",
                        action_type=ACTION_TYPE_AUTOMATION,
                        action_name="play_music",
                        parameters={
                            "tool_name": "play_music",
                            "parameters": {"query": goal},
                        },
                        retries=self.settings.workflow_default_retries,
                        position=0,
                    ),
                ),
            )

        return WorkflowPlan(
            goal=goal,
            name="Productivity Workflow",
            description="A safe starter workflow for a general productivity goal.",
            steps=(
                WorkflowStepPlan(
                    key="acknowledge_goal",
                    name="Acknowledge goal",
                    action_type=ACTION_TYPE_NOOP,
                    parameters={"message": f"Preparing workflow for: {goal}"},
                    position=0,
                ),
                WorkflowStepPlan(
                    key="notify_ready",
                    name="Send workflow reminder",
                    action_type=ACTION_TYPE_NOTIFICATION,
                    parameters={"message": f"Workflow ready: {goal}"},
                    depends_on=("acknowledge_goal",),
                    position=1,
                ),
            ),
        )

    def _study_plan(self, goal: str) -> WorkflowPlan:
        topic = self._extract_study_topic(goal)
        query_topic = quote_plus(topic)
        return WorkflowPlan(
            goal=goal,
            name=f"{topic} Study Session",
            description="Prepare a focused study workspace and start Study Mode.",
            source="heuristic",
            metadata={"workflow_type": "study_session", "topic": topic},
            steps=(
                WorkflowStepPlan(
                    key="open_vscode",
                    name="Open VS Code",
                    action_type=ACTION_TYPE_AUTOMATION,
                    action_name="open_app",
                    parameters={
                        "tool_name": "open_app",
                        "parameters": {"app_name": "vscode"},
                    },
                    retries=self.settings.workflow_default_retries,
                    timeout_seconds=self.settings.workflow_step_timeout_seconds,
                    position=0,
                ),
                WorkflowStepPlan(
                    key="open_notebook",
                    name="Open notebook",
                    action_type=ACTION_TYPE_AUTOMATION,
                    action_name="open_website",
                    parameters={
                        "tool_name": "open_website",
                        "parameters": {"url": "https://colab.research.google.com/"},
                    },
                    depends_on=("open_vscode",),
                    retries=self.settings.workflow_default_retries,
                    timeout_seconds=self.settings.workflow_step_timeout_seconds,
                    position=1,
                ),
                WorkflowStepPlan(
                    key="start_study_mode",
                    name="Start Study Mode",
                    action_type=ACTION_TYPE_STUDY_SESSION,
                    action_name="start",
                    parameters={"topic": topic},
                    depends_on=("open_vscode",),
                    retries=0,
                    position=2,
                ),
                WorkflowStepPlan(
                    key="open_reference_material",
                    name="Open reference material",
                    action_type=ACTION_TYPE_AUTOMATION,
                    action_name="open_website",
                    parameters={
                        "tool_name": "open_website",
                        "parameters": {
                            "url": f"https://www.google.com/search?q={query_topic}+study+resources"
                        },
                    },
                    depends_on=("start_study_mode",),
                    retries=self.settings.workflow_default_retries,
                    timeout_seconds=self.settings.workflow_step_timeout_seconds,
                    position=3,
                ),
                WorkflowStepPlan(
                    key="start_focus_timer",
                    name="Start focus timer",
                    action_type=ACTION_TYPE_NOTIFICATION,
                    action_name="notify",
                    parameters={
                        "message": (
                            f"Focus timer started for {self.settings.focus_target_minutes} "
                            f"minutes: {topic}"
                        )
                    },
                    depends_on=("start_study_mode",),
                    position=4,
                ),
            ),
        )

    def _try_ai_plan(self, goal: str) -> WorkflowPlan | None:
        prompt = self._planning_prompt(goal)
        try:
            raw_response = self.ollama_service.generate(prompt)
            payload = self._extract_json(raw_response)
            plan = plan_from_dict(payload)
            return WorkflowPlan(
                id=plan.id,
                goal=goal,
                name=plan.name,
                description=plan.description,
                source="ollama",
                metadata=plan.metadata,
                steps=plan.steps,
            )
        except Exception as exc:
            logger.info("Using heuristic workflow plan after AI planning failed: %s", exc)
            return None

    def _planning_prompt(self, goal: str) -> str:
        return (
            "Create a Cherry AI workflow plan as JSON only. "
            "Allowed action_type values: automation_tool, study_session, "
            "notification, noop. For automation_tool, parameters must include "
            "tool_name and parameters. Allowed tool_name values are open_app, "
            "open_website, play_music, take_screenshot, open_study_workspace. "
            "Keep steps deterministic and safe.\n\n"
            "Return shape: {\"name\":\"...\",\"description\":\"...\",\"steps\":["
            "{\"key\":\"open_vscode\",\"name\":\"Open VS Code\","
            "\"action_type\":\"automation_tool\",\"action_name\":\"open_app\","
            "\"parameters\":{\"tool_name\":\"open_app\",\"parameters\":{\"app_name\":\"vscode\"}},"
            "\"depends_on\":[],\"retries\":1}]}\n\n"
            f"Goal: {goal}"
        )

    def _extract_json(self, raw_response: str) -> dict[str, object]:
        stripped = raw_response.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return json.loads(stripped)
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("No JSON object found in workflow plan response.")
        return json.loads(stripped[start : end + 1])

    def _fallback_plan_explanation(self, plan: WorkflowPlan) -> str:
        lines = [f"{plan.name}: {plan.description or plan.goal}"]
        for index, step in enumerate(plan.steps, start=1):
            lines.append(f"{index}. {step.name}")
        return "\n".join(lines)

    def _clean_goal(self, goal: str) -> str:
        cleaned = goal.strip()
        if not cleaned:
            raise ValueError("Workflow goal is required.")
        return cleaned[:500]

    def _extract_study_topic(self, goal: str) -> str:
        cleaned = re.sub(
            r"\b(prepare|start|create|run|schedule|study|session|mode|for)\b",
            " ",
            goal,
            flags=re.IGNORECASE,
        )
        topic = " ".join(cleaned.split()).strip(" .:-")
        return topic or "Focused study"
