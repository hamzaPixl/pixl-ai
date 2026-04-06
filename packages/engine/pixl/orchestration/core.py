"""Core orchestrator functionality - base class and helpers."""

import asyncio
import contextlib
import logging
import os
import queue
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from claude_agent_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    query,
)

from pixl.agents.registry import AgentRegistry
from pixl.agents.sdk_options import ThinkingConfig, _resolve_crew_plugin_path, build_sdk_options
from pixl.config.providers import load_providers_config
from pixl.models.event import Event, EventType
from pixl.models.feature import Feature
from pixl.orchestration.background_manager import BackgroundManager
from pixl.orchestration.concurrency import ConcurrencyManager
from pixl.orchestration.external_provider import (
    get_provider_name,
    is_sdk_provider,
    query_external_provider,
    truncate_tool_input,
)
from pixl.output import console, is_json_mode
from pixl.paths import get_global_pixl_dir
from pixl.providers import ProviderRegistry
from pixl.storage import BacklogStore, BoulderStore, ConfigStore

logger = logging.getLogger(__name__)

# Safety timeout for a single SDK query (seconds). Prevents indefinite hangs.
_SDK_QUERY_TIMEOUT = int(os.environ.get("PIXL_SDK_QUERY_TIMEOUT", "600"))

# Circuit breaker: abort after this many repeated unrecoverable API errors.
_API_ERROR_CIRCUIT_BREAKER = 5

# Substrings that indicate an unrecoverable API error (conversation is
# corrupted and retrying the same request will never succeed).
_UNRECOVERABLE_ERROR_PATTERNS = (
    "tool_use.name: String should have at most",
    "tool_use.name: string length must be",
    "messages.*.content.*.tool_use.name:",
)


def _is_unrecoverable_api_error(text: str) -> bool:
    """Return True if *text* describes an API error that will never self-resolve."""
    if not text:
        return False
    return any(pat in text for pat in _UNRECOVERABLE_ERROR_PATTERNS)


class OrchestratorCore:
    """Core orchestrator with initialization and helper methods."""

    # Providers that use claude_agent_sdk for query execution.
    _SDK_PROVIDERS = {"anthropic"}

    def __init__(
        self,
        project_path: Path,
    ) -> None:
        self.project_path = project_path
        self.backlog_store = BacklogStore(project_path)
        self.boulder_store = BoulderStore(project_path)
        self.config_store = ConfigStore(project_path)

        # Providers configuration
        self.providers_config = load_providers_config(project_path)

        # Provider registry for backwards compatibility
        self.provider_registry = ProviderRegistry()

        # Concurrency manager for parallel execution
        self.concurrency = ConcurrencyManager(
            self.providers_config.concurrency,
            providers_config=self.providers_config,
        )

        # Background manager for fire-and-forget tasks
        self.background = BackgroundManager(
            concurrency_config=self.providers_config.concurrency,
            project_path=project_path,
        )

        # SDK event callback for real-time tracing (set by GraphExecutor)
        self._sdk_event_callback: Callable[[Event], None] | None = None
        self._sdk_session_id: str | None = None
        self._sdk_node_id: str | None = None

        # Persistent SDK clients keyed by (agent_name, resolved_model)
        self._sdk_clients: dict[tuple[str, str], ClaudeSDKClient] = {}
        self._sdk_clients_connected: set[tuple[str, str]] = set()

        # Locked tool sets per (agent_name, model)
        self._locked_tools: dict[tuple[str, str], list[str] | None] = {}

        # Interrupt signal (hard stop — binary)
        self._interrupt_event = threading.Event()

        # Steering queue (soft redirect — inject new instructions mid-task)
        self._steering_queue: queue.Queue[str] = queue.Queue()

        # Agent registry — parse crew agents for SDK delegation (GAP-02)
        self.agent_registry = AgentRegistry()
        crew_path = _resolve_crew_plugin_path()
        if crew_path:
            self.agent_registry.load_from_crew(Path(crew_path))

    async def _get_or_create_client(
        self,
        agent_name: str | None,
        model: str,
        options: ClaudeAgentOptions,
    ) -> ClaudeSDKClient:
        """Get or create a persistent SDK client for an agent+model combo."""
        key = (agent_name or "_default", model)
        if key not in self._sdk_clients:
            client = ClaudeSDKClient(options=options)
            self._sdk_clients[key] = client
            self._locked_tools[key] = getattr(options, "allowed_tools", None)
            logger.debug(
                "Created persistent client %s with locked tools: %s",
                key,
                self._locked_tools[key],
            )
        else:
            client = self._sdk_clients[key]
            new_tools = getattr(options, "allowed_tools", None)
            locked = self._locked_tools.get(key)
            if new_tools and locked and set(new_tools) != set(locked):
                extra = set(new_tools) - set(locked)
                if extra:
                    logger.info(
                        "Persistent client %s: expanding locked tools with %s",
                        key,
                        extra,
                    )
                    self._locked_tools[key] = list(set(locked) | set(new_tools))
        return client

    async def cleanup_sdk_clients(self) -> None:
        """Disconnect all persistent SDK clients. Call on workflow end."""
        for key, client in list(self._sdk_clients.items()):
            try:
                if key in self._sdk_clients_connected:
                    await client.disconnect()
            except Exception:
                logger.debug("Failed to disconnect SDK client %s", key, exc_info=True)
        self._sdk_clients.clear()
        self._sdk_clients_connected.clear()
        self._locked_tools.clear()

    def request_interrupt(self) -> None:
        """Signal any active SDK query to stop."""
        self._interrupt_event.set()

    def clear_interrupt(self) -> None:
        """Reset the interrupt signal."""
        self._interrupt_event.clear()

    def steer(self, instruction: str) -> None:
        """Queue a steering instruction for mid-task redirect.

        Unlike ``request_interrupt`` (hard stop), this injects a new user
        instruction at the next tool boundary.  The agent summarises
        progress and continues with the new instruction.
        """
        self._steering_queue.put(instruction)

    def _pop_steering_instruction(self) -> str | None:
        """Return the next queued steering instruction, or *None*."""
        try:
            return self._steering_queue.get_nowait()
        except queue.Empty:
            return None

    def _get_provider_name(self, model: str) -> str:
        return get_provider_name(self.providers_config, model)

    def _is_sdk_provider(self, model: str) -> bool:
        return is_sdk_provider(self.providers_config, model, self._SDK_PROVIDERS)

    @contextlib.contextmanager
    def _stage_env_context(
        self,
        *,
        session_id: str | None = None,
        stage_id: str | None = None,
        storage_project: str | None = None,
    ):
        """Inject deterministic stage context for artifact CLI/tooling."""
        updates = {
            "PIXL_SESSION_ID": session_id,
            "PIXL_STAGE_ID": stage_id,
            "PIXL_STORAGE_PROJECT": storage_project,
            "PIXL_ACTIVE_STORAGE_MODE": "standalone",
            "PIXL_ACTIVE_GLOBAL_DIR": str(get_global_pixl_dir()),
            # Reduce hook noise in SDK sessions — only critical hooks
            # (avoids AbortError spam from quality/advisory hooks on teardown)
            "PIXL_HOOK_PROFILE": "minimal",
            # Unset CLAUDECODE so SDK can spawn nested Claude Code sessions
            # (the parent session sets CLAUDECODE=1 which blocks nesting)
            "CLAUDECODE": None,
        }
        previous: dict[str, str | None] = {}
        for key, value in updates.items():
            previous[key] = os.environ.get(key)
            if value is None or value == "":
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(value)
        try:
            yield
        finally:
            for key, old in previous.items():
                if old is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old

    async def _query_external_provider(
        self,
        prompt: str,
        model: str,
        stream_callback: Callable[[Any], None] | None = None,
        workflow_tags: list[str] | None = None,
        stage_id: str | None = None,
        agent_name: str | None = None,
        extra_writable_dirs: list[str] | None = None,
        cwd: Path | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Route a query to a non-Anthropic provider."""
        return await query_external_provider(
            prompt,
            model,
            providers_config=self.providers_config,
            provider_registry=self.provider_registry,
            project_path=self.project_path,
            stream_callback=stream_callback,
            workflow_tags=workflow_tags,
            stage_id=stage_id,
            agent_name=agent_name,
            extra_writable_dirs=extra_writable_dirs,
            emit_sdk_event=self._emit_sdk_event if self._sdk_event_callback else None,
            sdk_session_id=self._sdk_session_id,
            sdk_node_id=self._sdk_node_id,
            cwd=cwd,
        )

    def _resolve_model(self, model: str) -> str:
        _, resolved_name = self.providers_config.parse_model_string(model)
        resolved_name = resolved_name or model

        if resolved_name != model:
            console.model_resolved(model, resolved_name)

        return resolved_name

    def _build_query_options(
        self,
        model: str = "claude-sonnet-4-6",
        extra_tools: list[str] | None = None,
        max_turns: int = 50,
        cwd: Path | None = None,
        agents: dict[str, AgentDefinition] | None = None,
        resume_session_id: str | None = None,
        continue_conversation: bool = False,
        system_prompt: str | None = None,
        max_budget_usd: float | None = None,
        fallback_model: str | None = None,
        output_format: dict[str, Any] | None = None,
        fork_session: bool = False,
        thinking: "str | dict[str, Any] | ThinkingConfig | None" = None,  # type: ignore[reportInvalidTypeForm]
        effort: "Literal['low', 'medium', 'high', 'max'] | None" = None,
        agent_name: str | None = None,
    ) -> ClaudeAgentOptions:
        """Build ClaudeAgentOptions with resolved model."""
        resolved_model = self._resolve_model(model)

        # Resolve per-agent tool restrictions from registry (GAP-06)
        allowed_tools = None
        if agent_name and self.agent_registry:
            agent_def = self.agent_registry.get_agent_definition(agent_name)
            if agent_def and agent_def.tools:
                allowed_tools = list(agent_def.tools)

        # Use minimal hook profile for SDK workflow sessions to avoid
        # AbortError spam from quality/advisory hooks on session teardown.
        # Hooks are loaded BOTH as SDK callbacks and via the plugins system;
        # crew_hook_profile filters SDK callbacks, env propagates to child process.
        hook_profile = os.environ.get("PIXL_HOOK_PROFILE", "minimal")

        return build_sdk_options(
            project_path=self.project_path,
            allowed_tools=allowed_tools,
            extra_tools=extra_tools,
            agents=agents,
            max_turns=max_turns,
            model=resolved_model,
            cwd=cwd or self.project_path,
            resume_session_id=resume_session_id,
            continue_conversation=continue_conversation,
            enable_safety_hooks=True,
            system_prompt=system_prompt,
            max_budget_usd=max_budget_usd,
            fallback_model=fallback_model,
            output_format=output_format,
            fork_session=fork_session,
            thinking=thinking,
            effort=effort,
            agent_registry=self.agent_registry,
            crew_hook_profile=hook_profile,
        )

    def get_feature(self, feature_id: str) -> Feature | None:
        return self.backlog_store.get_feature(feature_id)

    async def _process_streaming_message(
        self,
        message: Any,
        *,
        sdk_result_ref: list,
        stream_callback: Callable | None,
        api_error_count: int,
        result_text: str,
        stage_id: str | None = None,
        agent_name: str | None = None,
        on_interrupt: Callable[[], Any] | None = None,
        on_circuit_breaker: Callable[[], Any] | None = None,
    ) -> tuple[int, str, str | None, bool]:
        """Process a single streaming message.

        Returns (api_error_count, result_text, error_message, should_abort).
        """
        if isinstance(message, ResultMessage):
            sdk_result_ref[0] = message
            if message.result:
                result_text = message.result
            return api_error_count, result_text, None, False

        if self._interrupt_event.is_set():
            logger.info("SDK query interrupted (pause/stop)")
            if on_interrupt:
                with contextlib.suppress(Exception):
                    await on_interrupt()
            return (
                api_error_count,
                result_text,
                "Query interrupted (session paused or stopped)",
                True,
            )

        # Steering queue: soft redirect with new instruction (persistent client only).
        steering_instruction = self._pop_steering_instruction()
        if steering_instruction is not None:
            if on_interrupt:
                logger.info("Steering redirect: injecting new instruction (stage=%s)", stage_id)
                with contextlib.suppress(Exception):
                    await on_interrupt()
                return (
                    api_error_count,
                    result_text,
                    f"__STEER__:{steering_instruction}",
                    True,
                )
            else:
                logger.warning(
                    "Steering instruction received but no persistent client available "
                    "(one-shot path). Instruction discarded: %s",
                    steering_instruction[:80],
                )

        if hasattr(message, "content"):
            for block in message.content:
                if (
                    hasattr(block, "text")
                    and block.text
                    and _is_unrecoverable_api_error(block.text)
                ):
                    api_error_count += 1

        if api_error_count >= _API_ERROR_CIRCUIT_BREAKER:
            logger.error(
                "Circuit breaker tripped: %d repeated API errors, "
                "aborting query (stage=%s agent=%s)",
                api_error_count,
                stage_id,
                agent_name,
            )
            error_msg = (
                f"Unrecoverable API error loop detected ({api_error_count} repeated errors)."
            )
            if on_circuit_breaker:
                await on_circuit_breaker()
            elif on_interrupt:
                with contextlib.suppress(Exception):
                    await on_interrupt()
            return api_error_count, result_text, error_msg, True

        self._emit_sdk_events_for_message(message)

        if not is_json_mode() and stream_callback is None:
            self._stream_message(message)
        elif stream_callback:
            stream_callback(message)

        if hasattr(message, "content"):
            for block in message.content:
                if hasattr(block, "text") and block.text:
                    result_text = block.text

        return api_error_count, result_text, None, False

    async def send_session_command(
        self,
        command: str,
        options: ClaudeAgentOptions | None = None,
    ) -> None:
        """Send a slash command to manage session state."""

        if options is None:
            options = self._build_query_options(max_turns=1)

        async for _message in query(prompt=command, options=options):
            pass

    async def query_with_streaming(
        self,
        prompt: str,
        model: str,
        max_turns: int,
        feature_id: str,
        stream_callback: Callable[[Any], None] | None = None,
        workflow_tags: list[str] | None = None,
        stage_id: str | None = None,
        agent_name: str | None = None,
        resume_session_id: str | None = None,
        continue_conversation: bool = False,
        extra_writable_dirs: list[str] | None = None,
        session_id: str | None = None,
        storage_project: str | None = None,
        cwd: Path | None = None,
        output_format: dict[str, Any] | None = None,
        fork_session: bool = False,
        thinking: "str | dict[str, Any] | ThinkingConfig | None" = None,  # type: ignore[reportInvalidTypeForm]
        effort: "Literal['low', 'medium', 'high', 'max'] | None" = None,
        artifacts_dir: str | None = None,
    ) -> tuple[str, dict]:
        """Execute SDK query with optional streaming callback."""
        import time

        start_time = time.time()

        system_prompt_text: str | None = None

        if not self._is_sdk_provider(model):
            console.info(f"Using external provider for model: {model}")
            try:
                with self._stage_env_context(
                    session_id=session_id,
                    stage_id=stage_id,
                    storage_project=storage_project,
                ):
                    result_text, provider_metadata = await self._query_external_provider(
                        prompt=prompt,
                        model=model,
                        stream_callback=stream_callback,
                        workflow_tags=workflow_tags,
                        stage_id=stage_id,
                        agent_name=agent_name,
                        extra_writable_dirs=extra_writable_dirs,
                        cwd=cwd,
                    )
                duration = time.time() - start_time
                metadata: dict[str, Any] = {
                    "duration_seconds": duration,
                    "success": True,
                    "error": None,
                }
                metadata.update(provider_metadata)
                return result_text, metadata
            except Exception as e:
                duration = time.time() - start_time
                if not is_json_mode():
                    console.error(f"Provider error: {e}")
                return "", {
                    "duration_seconds": duration,
                    "success": False,
                    "error": str(e),
                }

        # Anthropic SDK path
        result_text = ""
        sdk_result: ResultMessage | None = None
        error_message = None

        options_kwargs: dict[str, Any] = {
            "model": model,
            "max_turns": max_turns,
            "cwd": cwd,
            "agent_name": agent_name,
        }
        if resume_session_id:
            options_kwargs["resume_session_id"] = resume_session_id
        if continue_conversation:
            options_kwargs["continue_conversation"] = True
        if system_prompt_text:
            options_kwargs["system_prompt"] = system_prompt_text

        model_budget = _model_budget_usd(model)
        if model_budget is not None:
            options_kwargs["max_budget_usd"] = model_budget

        fallback = _fallback_model_for(model)
        if fallback:
            options_kwargs["fallback_model"] = fallback

        if output_format:
            options_kwargs["output_format"] = output_format

        if fork_session:
            options_kwargs["fork_session"] = True

        effective_thinking = thinking
        effective_effort = effort

        if effective_thinking is not None:
            options_kwargs["thinking"] = effective_thinking
        if effective_effort is not None:
            options_kwargs["effort"] = effective_effort

        options = self._build_query_options(**options_kwargs)

        if self._sdk_event_callback and self._sdk_session_id and self._sdk_node_id:
            self._emit_sdk_event(
                Event.sdk_query_started(
                    self._sdk_session_id,
                    self._sdk_node_id,
                    model,
                    prompt_preview=prompt[:200] if prompt else None,
                )
            )

        use_persistent_client = (
            not resume_session_id and not continue_conversation and not fork_session
        )

        try:
            with self._stage_env_context(
                session_id=session_id,
                stage_id=stage_id,
                storage_project=storage_project,
            ):
                logger.info(
                    "SDK query start: model=%s agent=%s stage=%s persistent=%s",
                    model,
                    agent_name,
                    stage_id,
                    use_persistent_client,
                )
                api_error_count = 0
                aborted = False

                if use_persistent_client:
                    client = await self._get_or_create_client(agent_name, model, options)
                    client_key = (agent_name or "_default", model)

                    if client_key not in self._sdk_clients_connected:
                        await client.connect()
                        self._sdk_clients_connected.add(client_key)

                    sdk_result_ref: list[ResultMessage | None] = [None]

                    async def _evict_client() -> None:
                        with contextlib.suppress(Exception):
                            await client.interrupt()
                        self._sdk_clients.pop(client_key, None)
                        self._sdk_clients_connected.discard(client_key)

                    await client.query(prompt)
                    async with asyncio.timeout(_SDK_QUERY_TIMEOUT):
                        async for message in client.receive_response():
                            (
                                api_error_count,
                                result_text,
                                error_message,
                                aborted,
                            ) = await self._process_streaming_message(
                                message,
                                sdk_result_ref=sdk_result_ref,
                                stream_callback=stream_callback,
                                api_error_count=api_error_count,
                                result_text=result_text,
                                stage_id=stage_id,
                                agent_name=agent_name,
                                on_interrupt=client.interrupt,
                                on_circuit_breaker=_evict_client,
                            )
                            if aborted:
                                break
                    sdk_result = sdk_result_ref[0]

                    # Disconnect after each query so the next stage gets a fresh
                    # subprocess and _read_messages() task.  The SDK's Query
                    # object exhausts its message stream after one response;
                    # reusing it returns empty instantly (0.0008s bug).
                    with contextlib.suppress(Exception):
                        await client.disconnect()
                    self._sdk_clients_connected.discard(client_key)
                else:
                    sdk_result_ref: list[ResultMessage | None] = [None]  # type: ignore[no-redef]
                    async with asyncio.timeout(_SDK_QUERY_TIMEOUT):
                        async for message in query(prompt=prompt, options=options):
                            (
                                api_error_count,
                                result_text,
                                error_message,
                                aborted,
                            ) = await self._process_streaming_message(
                                message,
                                sdk_result_ref=sdk_result_ref,
                                stream_callback=stream_callback,
                                api_error_count=api_error_count,
                                result_text=result_text,
                                stage_id=stage_id,
                                agent_name=agent_name,
                            )
                            if aborted:
                                break
                    sdk_result = sdk_result_ref[0]

                # Handle steering redirect: re-query with new instruction.
                if (
                    aborted
                    and error_message
                    and error_message.startswith("__STEER__:")
                    and use_persistent_client
                ):
                    steering_instruction = error_message[len("__STEER__:") :]
                    logger.info(
                        "Steering: re-connecting client for redirect (stage=%s)",
                        stage_id,
                    )
                    # Re-connect and send the steering instruction as a follow-up.
                    if client_key not in self._sdk_clients_connected:  # type: ignore[possibly-undefined]
                        await client.connect()  # type: ignore[possibly-undefined]
                        self._sdk_clients_connected.add(client_key)  # type: ignore[possibly-undefined]

                    steering_prompt = (
                        f"[REDIRECT] The user has sent a new instruction. "
                        f"Summarise your progress so far, then follow the new instruction:\n\n"
                        f"{steering_instruction}"
                    )
                    await client.query(steering_prompt)  # type: ignore[possibly-undefined]
                    async with asyncio.timeout(_SDK_QUERY_TIMEOUT):
                        async for message in client.receive_response():  # type: ignore[possibly-undefined]
                            (
                                api_error_count,
                                result_text,
                                error_message,
                                aborted,
                            ) = await self._process_streaming_message(
                                message,
                                sdk_result_ref=sdk_result_ref,
                                stream_callback=stream_callback,
                                api_error_count=0,
                                result_text=result_text,
                                stage_id=stage_id,
                                agent_name=agent_name,
                                on_interrupt=client.interrupt,  # type: ignore[possibly-undefined]
                                on_circuit_breaker=_evict_client,  # type: ignore[possibly-undefined]
                            )
                            if aborted:
                                break
                    sdk_result = sdk_result_ref[0]

                    with contextlib.suppress(Exception):
                        await client.disconnect()  # type: ignore[possibly-undefined]
                    self._sdk_clients_connected.discard(client_key)  # type: ignore[possibly-undefined]

                elif aborted and not is_json_mode():
                    console.error(f"Query aborted: {error_message}")

        except Exception as e:
            error_message = str(e)
            logger.error(
                "SDK query failed: model=%s agent=%s stage=%s error=%s",
                model,
                agent_name,
                stage_id,
                error_message,
            )
            if not is_json_mode():
                console.error(f"SDK error: {error_message}")
            if self._sdk_event_callback and self._sdk_session_id and self._sdk_node_id:
                self._emit_sdk_event(
                    Event.sdk_error(
                        self._sdk_session_id,
                        self._sdk_node_id,
                        str(e),
                    )
                )
            if use_persistent_client:
                client_key = (agent_name or "_default", model)
                self._sdk_clients.pop(client_key, None)
                self._sdk_clients_connected.discard(client_key)

        duration = time.time() - start_time

        metadata = {
            "duration_seconds": duration,
            "success": error_message is None,
            "error": error_message,
            "model": model,
            "provider": "anthropic",
        }

        if sdk_result and hasattr(sdk_result, "usage"):
            metadata["usage"] = sdk_result.usage
        if sdk_result and getattr(sdk_result, "session_id", None):
            metadata["sdk_session_id"] = sdk_result.session_id
        if sdk_result and getattr(sdk_result, "structured_output", None) is not None:
            metadata["structured_output"] = sdk_result.structured_output

        if sdk_result and hasattr(sdk_result, "usage") and sdk_result.usage:
            cache_creation = sdk_result.usage.get("cache_creation_input_tokens", 0)
            cache_read = sdk_result.usage.get("cache_read_input_tokens", 0)
            input_tokens = sdk_result.usage.get("input_tokens", 0)
            total_input = cache_creation + cache_read + input_tokens

            metadata["cache_creation_input_tokens"] = cache_creation
            metadata["cache_read_input_tokens"] = cache_read

            if total_input > 0:
                cache_hit_rate = cache_read / total_input
                metadata["cache_hit_rate"] = round(cache_hit_rate, 4)
                logger.info(
                    "prompt_cache: agent=%s stage=%s model=%s "
                    "cache_read=%d cache_creation=%d input=%d "
                    "hit_rate=%.1f%%",
                    agent_name,
                    stage_id,
                    model,
                    cache_read,
                    cache_creation,
                    input_tokens,
                    cache_hit_rate * 100,
                )
                if cache_read == 0 and cache_creation > 0:
                    logger.warning(
                        "prompt_cache_miss: agent=%s stage=%s — "
                        "no cache reads with %d creation tokens.",
                        agent_name,
                        stage_id,
                        cache_creation,
                    )

        if self._sdk_event_callback and self._sdk_session_id and self._sdk_node_id:
            total_tokens = None
            usage_data = None
            if sdk_result and hasattr(sdk_result, "usage") and sdk_result.usage:
                total_tokens = sdk_result.usage.get("total_tokens")
                usage_data = sdk_result.usage
            self._emit_sdk_event(
                Event.sdk_query_completed(
                    self._sdk_session_id,
                    self._sdk_node_id,
                    duration,
                    num_turns=sdk_result.num_turns if sdk_result else None,
                    total_tokens=total_tokens,
                    usage=usage_data,
                )
            )

        return result_text, metadata

    def _stream_message(self, message: Any) -> None:
        """Stream SDK message content to terminal in real-time."""
        if not hasattr(message, "content"):
            return

        for block in message.content:
            if hasattr(block, "name"):
                tool_input = getattr(block, "input", {})
                console.stream_tool_call(block.name, tool_input)
            elif hasattr(block, "thinking"):
                console.stream_thinking(block.thinking)
            elif hasattr(block, "text") and block.text:
                console.stream_text(block.text)

    def _emit_sdk_events_for_message(self, message: Any) -> None:
        """Emit SDK events for tool calls, tool results, and thinking blocks."""
        if not self._sdk_event_callback or not self._sdk_session_id or not self._sdk_node_id:
            return

        if not hasattr(message, "content"):
            return

        tool_names: dict[str, str] = {}
        for block in message.content:
            if hasattr(block, "name"):
                use_id = getattr(block, "id", None)
                if use_id:
                    tool_names[use_id] = block.name
                tool_input = getattr(block, "input", {})
                self._emit_sdk_event(
                    Event.sdk_tool_call_started(
                        self._sdk_session_id,
                        self._sdk_node_id,
                        block.name,
                        truncate_tool_input(tool_input),
                    )
                )
                if block.name in ("Write", "Edit", "NotebookEdit"):
                    file_path = tool_input.get("file_path", "")
                    if file_path:
                        event_type = (
                            EventType.ARTIFACT_CREATED
                            if block.name == "Write"
                            else EventType.ARTIFACT_MODIFIED
                        )
                        self._emit_sdk_event(
                            Event.create(
                                event_type,
                                self._sdk_session_id,
                                node_id=self._sdk_node_id,
                                data={"file_path": file_path, "tool": block.name},
                            )
                        )
            elif hasattr(block, "type") and getattr(block, "type", None) == "tool_result":
                use_id = getattr(block, "tool_use_id", None)
                tool_name = tool_names.get(use_id, "unknown") if use_id else "unknown"
                is_error = getattr(block, "is_error", False)
                content = getattr(block, "content", "")
                error_msg = str(content) if is_error and content else None
                self._emit_sdk_event(
                    Event.sdk_tool_call_completed(
                        self._sdk_session_id,
                        self._sdk_node_id,
                        tool_name,
                        is_error=is_error,
                        error_message=error_msg,
                    )
                )
            elif hasattr(block, "thinking"):
                self._emit_sdk_event(
                    Event.sdk_thinking_started(
                        self._sdk_session_id,
                        self._sdk_node_id,
                    )
                )
            elif hasattr(block, "text") and block.text:
                self._emit_sdk_event(
                    Event.sdk_text_delta(
                        self._sdk_session_id,
                        self._sdk_node_id,
                        block.text[:500] if len(block.text) > 500 else block.text,
                    )
                )

    # SDK Event Emission

    def set_sdk_event_callback(
        self,
        callback: Callable[["Event"], None],
        session_id: str,
        node_id: str,
    ) -> None:
        self._sdk_event_callback = callback
        self._sdk_session_id = session_id
        self._sdk_node_id = node_id

    def clear_sdk_event_callback(self) -> None:
        self._sdk_event_callback = None
        self._sdk_session_id = None
        self._sdk_node_id = None

    def _emit_sdk_event(self, event: "Event") -> None:
        if self._sdk_event_callback is not None:
            try:
                self._sdk_event_callback(event)
            except Exception:
                logger.exception("Failed to emit SDK event")


# Model tier helpers (SDK provider only)

_BUDGET_BY_TIER: dict[str, float] = {
    "haiku": 0.50,
    "sonnet": 2.00,
    "opus": 5.00,
}

_FALLBACK_MAP: dict[str, str] = {
    "opus": "claude-sonnet-4-6",
    "sonnet": "claude-haiku-4-5",
}


def _model_tier(model: str) -> str | None:
    lower = model.lower()
    if "opus" in lower:
        return "opus"
    if "sonnet" in lower:
        return "sonnet"
    if "haiku" in lower:
        return "haiku"
    return None


def _model_budget_usd(model: str) -> float | None:
    tier = _model_tier(model)
    return _BUDGET_BY_TIER.get(tier) if tier else None


def _fallback_model_for(model: str) -> str | None:
    tier = _model_tier(model)
    return _FALLBACK_MAP.get(tier) if tier else None


__all__ = ["OrchestratorCore"]
