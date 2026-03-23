"""Async Python client wrapping the Gemini CLI binary.

This module provides :class:`GeminiCLIClient`, which manages the CLI
subprocess lifecycle, streams typed events, and handles fallback from
``stream-json`` to ``json`` output format for older CLI versions.

Usage::

    client = GeminiCLIClient()
    async for event in client.query("Summarise this repo", cwd="/my/project"):
        print(event)
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import shutil
from collections.abc import AsyncIterator
from pathlib import Path

from pixl.providers.gemini.auth import (
    has_oauth_credentials,
    oauth_credentials_path,
    warn_if_api_key_set,
)
from pixl.providers.gemini.models import (
    ErrorEvent,
    GeminiEvent,
    MessageEvent,
    ResultEvent,
)
from pixl.providers.gemini.parser import (
    extract_usage_from_json_stats,
    parse_json_payload,
    parse_line,
)

logger = logging.getLogger(__name__)

# Subprocess buffer limit: 4 MiB to handle large tool outputs.
_SUBPROCESS_BUFFER = 4 * 1024 * 1024


class CLINotFoundError(RuntimeError):
    """Raised when the ``gemini`` binary is not on ``$PATH``."""


class OAuthNotConfiguredError(RuntimeError):
    """Raised when OAuth credentials have not been set up."""


class GeminiCLIClient:
    """Async Python client wrapping the Gemini CLI binary.

    The client is stateless and safe to reuse across calls.

    Parameters
    ----------
    executable:
        Path to the ``gemini`` binary.  Defaults to finding it on ``$PATH``.
    """

    def __init__(self, executable: str | None = None, timeout: float = 300.0) -> None:
        self._executable = executable or "gemini"
        self._timeout = timeout

    # Public API

    async def query(
        self,
        prompt: str,
        *,
        model: str | None = None,
        cwd: str | None = None,
        yolo: bool = False,
        sandbox: bool = True,
        extra_dirs: list[str] | None = None,
        resume_session_id: str | None = None,
    ) -> AsyncIterator[GeminiEvent]:
        """Stream typed events from the Gemini CLI.

        Parameters
        ----------
        prompt:
            The prompt to send to the model.
        model:
            Optional model name (e.g. ``gemini-3-pro-preview``).
        cwd:
            Working directory for the CLI process.
        yolo:
            If ``True``, pass ``--approval-mode yolo`` to auto-approve edits.
        sandbox:
            If ``True`` and ``yolo`` is set, enable the sandbox.
        extra_dirs:
            Additional directories to include via ``--include-directories``.
        resume_session_id:
            If set, resume a previous CLI session via ``--resume``.
        """
        self._preflight_checks()
        warn_if_api_key_set()

        resolved_cwd = cwd or os.getcwd()
        extra = extra_dirs or []

        # ── Primary path: stream-json ──
        cmd = self._build_command(
            prompt,
            model=model,
            output_format="stream-json",
            yolo=yolo,
            sandbox=sandbox,
            extra_dirs=extra,
            cwd=resolved_cwd,
            resume_session_id=resume_session_id,
        )

        parsed_events = 0
        malformed_lines = 0
        emitted_chunks = False

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=_SUBPROCESS_BUFFER,
            env=os.environ.copy(),
            cwd=resolved_cwd,
        )

        try:
            assert process.stdout is not None  # noqa: S101
            async with asyncio.timeout(self._timeout):
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break

                    line_str = line.decode(errors="replace").strip()
                    if not line_str:
                        continue  # Blank line — not malformed

                    event = parse_line(line_str)
                    if event is None:
                        malformed_lines += 1
                        logger.debug("Malformed stream-json line: %s", line_str[:200])
                        continue

                    parsed_events += 1
                    emitted_chunks = True
                    yield event

            await process.wait()
            assert process.stderr is not None  # noqa: S101
            stderr_text = (await process.stderr.read()).decode(errors="replace").strip()

            # ── Fallback path: json ──
            if self._should_fallback(
                returncode=process.returncode or 0,
                parsed_events=parsed_events,
                malformed_lines=malformed_lines,
                emitted_chunks=emitted_chunks,
                stderr_text=stderr_text,
            ):
                logger.debug(
                    "Falling back to json output (rc=%s, events=%d, malformed=%d)",
                    process.returncode,
                    parsed_events,
                    malformed_lines,
                )
                async for event in self._run_json_fallback(
                    prompt,
                    model=model,
                    yolo=yolo,
                    sandbox=sandbox,
                    extra_dirs=extra,
                    cwd=resolved_cwd,
                ):
                    yield event
                return

            if process.returncode and process.returncode != 0:
                message = stderr_text or "Gemini CLI returned a non-zero exit code."
                yield ErrorEvent(message=f"Gemini CLI error: {message}")

        except TimeoutError:
            # Watchdog: kill hung process
            if process.returncode is None:
                process.kill()
                await process.wait()
            yield ErrorEvent(message=f"Gemini CLI timed out after {self._timeout}s")
        except Exception:
            if process.returncode is None:
                process.kill()
                await process.wait()
            raise

    # Command building

    def _build_command(
        self,
        prompt: str,
        *,
        model: str | None,
        output_format: str,
        yolo: bool,
        sandbox: bool,
        extra_dirs: list[str],
        cwd: str,
        resume_session_id: str | None = None,
    ) -> list[str]:
        # Positional prompt (replaces deprecated -p flag)
        cmd = [self._executable, prompt, "--output-format", output_format]

        if model:
            cmd.extend(["--model", model])

        if yolo:
            cmd.extend(["--approval-mode", "yolo"])
            if sandbox and self._should_enable_sandbox(cwd, extra_dirs):
                cmd.append("--sandbox")

        if resume_session_id:
            cmd.extend(["--resume", resume_session_id])

        for extra_dir in extra_dirs:
            cmd.extend(["--include-directories", extra_dir])

        return cmd

    # Preflight

    def _preflight_checks(self) -> None:
        """Raise if the CLI is missing or OAuth is not configured."""
        if not shutil.which(self._executable):
            raise CLINotFoundError(
                f"Gemini CLI not found (looked for '{self._executable}'). "
                "Install with: npm install -g @google/gemini-cli"
            )
        if not has_oauth_credentials():
            raise OAuthNotConfiguredError(
                "Gemini OAuth not configured. Run `gemini` in an interactive "
                f"terminal to authenticate first (expected creds at "
                f"{oauth_credentials_path()})."
            )

    # Sandbox heuristic

    @staticmethod
    def _should_enable_sandbox(cwd: str, extra_dirs: list[str]) -> bool:
        """Disable sandbox when extra dirs fall outside cwd.

        When agent stages need to write outside cwd (e.g. standalone DB
        storage roots), the sandbox blocks those writes. In that case keep
        YOLO approval but disable sandbox.
        """
        try:
            cwd_path = Path(cwd).resolve()
        except Exception:
            cwd_path = Path(cwd)

        for raw_path in extra_dirs:
            candidate = Path(raw_path)
            if not candidate.is_absolute():
                candidate = cwd_path / candidate
            with contextlib.suppress(Exception):
                candidate = candidate.resolve()
            try:
                candidate.relative_to(cwd_path)
            except ValueError:
                return False
        return True

    # Fallback: json output format

    @staticmethod
    def _should_fallback(
        *,
        returncode: int,
        parsed_events: int,
        malformed_lines: int,
        emitted_chunks: bool,
        stderr_text: str,
    ) -> bool:
        if emitted_chunks:
            return False

        stderr_lower = stderr_text.lower()
        stream_json_not_supported = (
            "--output-format" in stderr_text
            and "stream-json" in stderr_lower
            and (
                "invalid values" in stderr_lower
                or "unknown argument" in stderr_lower
                or "unknown option" in stderr_lower
            )
        )

        if stream_json_not_supported:
            return True
        if parsed_events == 0 and malformed_lines > 0:
            return True
        return bool(returncode == 0 and parsed_events == 0 and not stderr_text)

    async def _run_json_fallback(
        self,
        prompt: str,
        *,
        model: str | None,
        yolo: bool,
        sandbox: bool,
        extra_dirs: list[str],
        cwd: str,
    ) -> AsyncIterator[GeminiEvent]:
        cmd = self._build_command(
            prompt,
            model=model,
            output_format="json",
            yolo=yolo,
            sandbox=sandbox,
            extra_dirs=extra_dirs,
            cwd=cwd,
        )

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy(),
            cwd=cwd,
        )
        try:
            async with asyncio.timeout(self._timeout):
                stdout, stderr = await process.communicate()
        except TimeoutError:
            if process.returncode is None:
                process.kill()
                await process.wait()
            yield ErrorEvent(message=f"Gemini CLI JSON fallback timed out after {self._timeout}s")
            return

        stdout_text = stdout.decode(errors="replace").strip()
        stderr_text = stderr.decode(errors="replace").strip()

        payload = parse_json_payload(stdout_text) or parse_json_payload(stderr_text)

        if payload is None:
            if process.returncode != 0:
                message = stderr_text or stdout_text or "Gemini CLI JSON fallback failed"
                yield ErrorEvent(message=f"Gemini CLI error: {message}")
            elif stdout_text:
                yield MessageEvent(content=stdout_text)
            return

        response = payload.get("response")
        if isinstance(response, str) and response:
            yield MessageEvent(content=response)

        usage = extract_usage_from_json_stats(payload.get("stats"))
        if usage:
            yield ResultEvent(status="success", stats=usage)

        error = payload.get("error")
        if error:
            if isinstance(error, dict):
                message = str(error.get("message", "Unknown Gemini error"))
            else:
                message = str(error)
            yield ErrorEvent(message=message)
        elif process.returncode and process.returncode != 0:
            message = stderr_text or "Gemini CLI JSON fallback failed"
            yield ErrorEvent(message=f"Gemini CLI error: {message}")


__all__ = [
    "GeminiCLIClient",
    "CLINotFoundError",
    "OAuthNotConfiguredError",
]
