"""Prompt classifier for routing user prompts to the right workflow."""

import json
import re
from pathlib import Path

import yaml
from pydantic import ValidationError

from pixl.config.providers import load_providers_config
from pixl.routing.models import RouterResult

# ── Lightweight keyword classifier (no LLM call) ────────────────────────

_WORKFLOW_KEYWORDS: list[tuple[str, list[str]]] = [
    ("debug", ["fix ", "bug", "error", "broken", "failing", "crash", "debug", "issue", "wrong", "not working"]),
    ("tdd", ["test first", "tdd", "test-driven", "write tests"]),
    ("roadmap", ["roadmap", "milestone", "strategic plan", "multi-phase"]),
    ("decompose", ["decompose", "break down", "split into features", "epic", "multi-feature"]),
]


def classify_prompt_fast(prompt: str) -> str:
    """Lightweight keyword-based workflow classifier. No LLM call.

    Returns a workflow ID: 'debug', 'tdd', 'roadmap', 'decompose', or 'simple'.
    """
    lower = prompt.lower()
    for workflow_id, keywords in _WORKFLOW_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return workflow_id
    return "simple"

# Path to the bundled router prompt
ROUTER_PROMPT_PATH = (
    Path(__file__).parent.parent / "assets" / "prompts" / "router" / "classify.yaml"
)


class ClassificationError(Exception):
    """Raised when prompt classification fails."""


class PromptClassifier:
    """Classifies user prompts into feature/epic/roadmap categories.

    Uses a single-turn LLM call to analyze the prompt and return
    a structured RouterResult.
    """

    def __init__(self, project_path: Path, model: str | None = None) -> None:
        self.project_path = project_path
        self.model = model or load_providers_config(project_path).default_model

    def _load_prompt_template(self) -> str:
        """Load the router classification prompt from YAML."""
        if not ROUTER_PROMPT_PATH.exists():
            raise ClassificationError(f"Router prompt template not found: {ROUTER_PROMPT_PATH}")
        with open(ROUTER_PROMPT_PATH) as f:
            data = yaml.safe_load(f)
        result: str = str(data.get("prompt", ""))
        return result

    def _build_prompt(self, user_prompt: str) -> str:
        """Build the full classification prompt."""
        template = self._load_prompt_template()
        return template.replace("{user_prompt}", user_prompt)

    def _parse_response(self, response: str) -> RouterResult:
        """Parse LLM response into RouterResult.

        Handles markdown code fences around JSON.
        """
        # Strip markdown code fences
        cleaned = response.strip()
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ClassificationError(
                f"Failed to parse router response as JSON: {e}\nResponse: {response[:500]}"
            ) from e

        try:
            return RouterResult.model_validate(data)
        except ValidationError as e:
            raise ClassificationError(
                f"Router response failed validation: {e}\nData: {data}"
            ) from e

    async def classify(self, prompt: str) -> RouterResult:
        """Classify a user prompt into a work kind.

        Args:
            prompt: The user's natural language prompt

        Returns:
            RouterResult with classification details

        Raises:
            ClassificationError: If classification fails after retries
        """
        from pixl.orchestration.core import OrchestratorCore

        orchestrator = OrchestratorCore(self.project_path)
        full_prompt = self._build_prompt(prompt)

        # First attempt
        response_text, metadata = await orchestrator.query_with_streaming(
            prompt=full_prompt,
            model=self.model,
            max_turns=1,
            feature_id="router",
        )

        try:
            return self._parse_response(response_text)
        except ClassificationError:
            pass

        retry_prompt = (
            f"{full_prompt}\n\n"
            "IMPORTANT: Respond ONLY with a valid JSON object. "
            "No markdown, no explanation, just the JSON."
        )

        response_text, metadata = await orchestrator.query_with_streaming(
            prompt=retry_prompt,
            model=self.model,
            max_turns=1,
            feature_id="router",
        )

        return self._parse_response(response_text)
