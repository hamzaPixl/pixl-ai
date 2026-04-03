"""Tests for workflow run schemas and streaming utilities."""

from __future__ import annotations

import asyncio
import json

import pytest
from pixl_api.schemas.run import (
    ClassifyRequest,
    ClassifyResponse,
    RunConfirmRequest,
    RunFeatureRequest,
    RunResponse,
)
from pixl_api.streaming import create_sse_response, workflow_event_generator

# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


class TestClassifyRequest:
    def test_valid_prompt(self) -> None:
        req = ClassifyRequest(prompt="Build a landing page")
        assert req.prompt == "Build a landing page"

    def test_empty_prompt_rejected(self) -> None:
        with pytest.raises(Exception):
            ClassifyRequest(prompt="")

    def test_max_length_prompt(self) -> None:
        long = "a" * 50000
        req = ClassifyRequest(prompt=long)
        assert len(req.prompt) == 50000

    def test_too_long_prompt_rejected(self) -> None:
        with pytest.raises(Exception):
            ClassifyRequest(prompt="a" * 50001)

    def test_optional_model(self) -> None:
        req = ClassifyRequest(prompt="Build a thing", model="claude-sonnet-4-5-20250514")
        assert req.model == "claude-sonnet-4-5-20250514"

    def test_model_defaults_none(self) -> None:
        req = ClassifyRequest(prompt="Build a thing")
        assert req.model is None


class TestClassifyResponse:
    def test_minimal(self) -> None:
        resp = ClassifyResponse(
            kind="feature",
            title="Build a landing page",
            suggested_workflow="simple",
        )
        assert resp.kind == "feature"
        assert resp.confidence is None
        assert resp.estimated_features == 1

    def test_full_response(self) -> None:
        resp = ClassifyResponse(
            kind="epic",
            confidence=0.95,
            title="Multi-tenant auth",
            suggested_workflow="decompose",
            estimated_features=5,
            why=["Complex scope"],
            risk_flags=["auth complexity"],
            suggested_sub_workflows=["tdd"],
        )
        assert resp.confidence == 0.95
        assert resp.estimated_features == 5
        assert len(resp.why) == 1
        assert len(resp.risk_flags) == 1


class TestRunConfirmRequest:
    def test_defaults(self) -> None:
        req = RunConfirmRequest(prompt="Add auth")
        assert req.workflow_id is None
        assert req.skip_approval is True
        assert req.kind == "feature"
        assert req.title == ""

    def test_explicit_workflow(self) -> None:
        req = RunConfirmRequest(prompt="Fix bug", workflow_id="debug", skip_approval=False)
        assert req.workflow_id == "debug"
        assert req.skip_approval is False

    def test_kind_and_title(self) -> None:
        req = RunConfirmRequest(prompt="Build auth system", kind="epic", title="Auth Epic")
        assert req.kind == "epic"
        assert req.title == "Auth Epic"


class TestRunFeatureRequest:
    def test_defaults(self) -> None:
        req = RunFeatureRequest()
        assert req.workflow_id is None
        assert req.skip_approval is True


class TestRunResponse:
    def test_all_fields(self) -> None:
        resp = RunResponse(
            session_id="s1", feature_id="f1", workflow_id="simple", status="completed", steps=5
        )
        assert resp.steps == 5

    def test_steps_default(self) -> None:
        resp = RunResponse(session_id="s1", feature_id="f1", workflow_id="simple", status="running")
        assert resp.steps == 0


# ---------------------------------------------------------------------------
# SSE streaming tests
# ---------------------------------------------------------------------------


class TestWorkflowEventGenerator:
    @pytest.mark.asyncio
    async def test_emits_events_then_done(self) -> None:
        queue: asyncio.Queue[dict] = asyncio.Queue()
        done = asyncio.Event()

        await queue.put({"type": "step", "data": {"n": 1}})
        await queue.put({"type": "step", "data": {"n": 2}})
        done.set()

        lines: list[str] = []
        async for line in workflow_event_generator(queue, done):
            lines.append(line)

        # Should have 2 events + 1 done marker
        assert len(lines) == 3
        assert '"type": "step"' in lines[0]
        assert '"type": "step"' in lines[1]
        assert '"type": "done"' in lines[2]

        # Each line should be SSE-formatted
        for line in lines:
            assert line.startswith("data: ")
            assert line.endswith("\n\n")

    @pytest.mark.asyncio
    async def test_keepalive_on_empty_queue(self) -> None:
        queue: asyncio.Queue[dict] = asyncio.Queue()
        done = asyncio.Event()

        # Signal done after a short delay so we get at least one keepalive
        async def signal_done() -> None:
            await asyncio.sleep(1.5)
            done.set()

        asyncio.create_task(signal_done())

        lines: list[str] = []
        async for line in workflow_event_generator(queue, done):
            lines.append(line)
            if len(lines) > 5:
                break  # Safety limit

        # Should have at least 1 keepalive + done
        keepalives = [ln for ln in lines if ln.startswith(": keepalive")]
        assert len(keepalives) >= 1

    @pytest.mark.asyncio
    async def test_done_event_is_json(self) -> None:
        queue: asyncio.Queue[dict] = asyncio.Queue()
        done = asyncio.Event()
        done.set()

        lines: list[str] = []
        async for line in workflow_event_generator(queue, done):
            lines.append(line)

        # Last line should be parseable JSON with type=done
        last = lines[-1]
        payload = json.loads(last.removeprefix("data: ").strip())
        assert payload["type"] == "done"


class TestCreateSseResponse:
    def test_returns_streaming_response(self) -> None:
        async def noop_gen():
            yield "data: {}\n\n"

        resp = create_sse_response(noop_gen())
        assert resp.media_type == "text/event-stream"
        assert resp.headers.get("cache-control") == "no-cache"
