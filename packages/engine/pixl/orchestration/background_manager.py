"""Background task manager for parallel agent execution."""

import asyncio
import contextlib
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from pixl.config.providers import ConcurrencyConfig, load_providers_config
from pixl.orchestration.background import BackgroundTask, TaskStatus
from pixl.orchestration.concurrency import ConcurrencyManager


@dataclass
class TaskHandle:
    """Handle returned when launching a task."""

    task_id: str
    status: TaskStatus


class BackgroundManager:
    """Manages background agent tasks."""

    def __init__(
        self,
        concurrency_config: ConcurrencyConfig | None = None,
        project_path: Path | None = None,
        *,
        sandbox_backend: object | None = None,
    ) -> None:
        self._tasks: dict[str, BackgroundTask] = {}
        self._asyncio_tasks: dict[str, asyncio.Task[None]] = {}

        self._project_path = project_path or Path.cwd()
        self._sandbox_backend = sandbox_backend
        self._providers_config = load_providers_config(self._project_path)
        config = concurrency_config or ConcurrencyConfig()
        self._concurrency = ConcurrencyManager(
            config, providers_config=self._providers_config
        )

    _MAX_FINISHED_TASKS = 500

    async def launch(
        self,
        agent: str,
        prompt: str,
        model: str | None = None,
    ) -> TaskHandle:
        """Launch a background task."""
        task_id = f"bg-{uuid.uuid4().hex[:8]}"
        model_string = model or "anthropic/claude-haiku-4-5"

        task = BackgroundTask(
            id=task_id,
            agent=agent,
            prompt=prompt,
            model=model_string,
        )
        self._tasks[task_id] = task

        if not self._concurrency.acquire(model_string):
            return TaskHandle(task_id=task_id, status=TaskStatus.PENDING)

        finished_count = sum(1 for t in self._tasks.values() if t.is_finished)
        if finished_count > self._MAX_FINISHED_TASKS:
            self.cleanup_finished()

        task.start()
        asyncio_task = asyncio.create_task(self._run_task(task))
        self._asyncio_tasks[task_id] = asyncio_task

        return TaskHandle(task_id=task_id, status=TaskStatus.RUNNING)

    async def _run_task(self, task: BackgroundTask) -> None:
        """Run a background task via OrchestratorCore (routes to Daytona when available)."""
        try:
            from pixl.orchestration.core import OrchestratorCore

            orchestrator = OrchestratorCore(
                self._project_path, sandbox_backend=self._sandbox_backend
            )
            result_text, metadata = await orchestrator.query_with_streaming(
                prompt=task.prompt,
                model=task.model or "claude-haiku-4-5",
                max_turns=50,
                feature_id="background",
                stage_id=task.id,
                agent_name=task.agent,
            )
            task.complete(result_text or "Completed")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            task.fail(str(e))
        finally:
            if task.model:
                self._concurrency.release(task.model)

    def get_task(self, task_id: str) -> BackgroundTask | None:
        return self._tasks.get(task_id)

    def list_all(self) -> list[BackgroundTask]:
        return list(self._tasks.values())

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.is_finished:
            return False

        asyncio_task = self._asyncio_tasks.get(task_id)
        if asyncio_task and not asyncio_task.done():
            asyncio_task.cancel()

        task.cancel()
        if task.model:
            self._concurrency.release(task.model)

        return True

    def cleanup_finished(self, max_age_seconds: float = 600.0) -> int:
        now = time.monotonic()
        to_remove: list[str] = []
        for task_id, task in self._tasks.items():
            if not task.is_finished:
                continue
            ended = getattr(task, "ended_at", None)
            if ended is not None and (now - ended) > max_age_seconds:
                to_remove.append(task_id)
            elif ended is None:
                to_remove.append(task_id)

        for task_id in to_remove:
            self._tasks.pop(task_id, None)
            self._asyncio_tasks.pop(task_id, None)

        return len(to_remove)

    async def shutdown(self) -> None:
        for task_id, asyncio_task in list(self._asyncio_tasks.items()):
            if not asyncio_task.done():
                asyncio_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await asyncio_task

        self._tasks.clear()
        self._asyncio_tasks.clear()
