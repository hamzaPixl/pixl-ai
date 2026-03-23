"""HTTP client for the pixl-sandbox Worker API.

Resolves sandbox URL and API key from:
1. PIXL_SANDBOX_URL / PIXL_SANDBOX_API_KEY env vars (or JWT via PIXL_SANDBOX_JWT_SECRET)
2. pixl config get sandbox_url / sandbox_api_key / sandbox_jwt_secret
"""

from __future__ import annotations

import json
import logging
import os
import threading
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def _generate_jwt(secret: str, expiry_minutes: int = 60, *, scope: str = "admin") -> str:
    """Generate a short-lived JWT for sandbox auth."""
    try:
        import jwt  # pyjwt — available via engine [api] extra
    except ImportError as exc:
        raise ImportError(
            "PyJWT is required for JWT auth. Install with: pip install pyjwt"
        ) from exc

    payload = {
        "iss": "pixl-cli",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
        "scope": scope,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


_REFRESH_BUFFER_MINUTES = 5


class SandboxClient:
    """Client for communicating with the pixl-sandbox Cloudflare Worker."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        scope: str = "admin",
        jwt_secret: str | None = None,
        expiry_minutes: int = 60,
    ) -> None:
        self._scope = scope
        self._jwt_secret = jwt_secret
        self._expiry_minutes = expiry_minutes
        self._token_generated_at: datetime | None = None
        self._refresh_lock = threading.Lock()

        # When a jwt_secret is provided, generate a scoped token immediately
        if jwt_secret:
            api_key = _generate_jwt(jwt_secret, expiry_minutes, scope=scope)
            self._token_generated_at = datetime.now(timezone.utc)

        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=300.0,
        )

    def _ensure_valid_token(self) -> None:
        """Refresh the JWT if it is within 5 minutes of expiry."""
        if self._jwt_secret is None or self._token_generated_at is None:
            return

        elapsed = datetime.now(timezone.utc) - self._token_generated_at
        remaining = timedelta(minutes=self._expiry_minutes) - elapsed
        if remaining > timedelta(minutes=_REFRESH_BUFFER_MINUTES):
            return

        with self._refresh_lock:
            # Double-check after acquiring lock
            elapsed = datetime.now(timezone.utc) - self._token_generated_at
            remaining = timedelta(minutes=self._expiry_minutes) - elapsed
            if remaining > timedelta(minutes=_REFRESH_BUFFER_MINUTES):
                return

            new_token = _generate_jwt(
                self._jwt_secret, self._expiry_minutes, scope=self._scope,
            )
            self._client.headers["authorization"] = f"Bearer {new_token}"
            self._token_generated_at = datetime.now(timezone.utc)

    def close(self) -> None:
        self._client.close()

    def create(
        self,
        project_id: str,
        *,
        repo_url: str | None = None,
        branch: str | None = None,
        env_vars: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a sandbox — single-call setup."""
        self._ensure_valid_token()
        body: dict[str, Any] = {"projectId": project_id}
        if repo_url:
            body["repoUrl"] = repo_url
        if branch:
            body["branch"] = branch

        # Auto-forward platform keys from local env
        forwarded: dict[str, str] = {}
        for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GITHUB_TOKEN"):
            val = os.environ.get(key)
            if val:
                forwarded[key] = val
        if env_vars:
            forwarded.update(env_vars)
        if forwarded:
            body["envVars"] = forwarded

        resp = self._client.post("/sandboxes", json=body)
        resp.raise_for_status()
        return resp.json()

    def destroy(self, project_id: str) -> dict[str, Any]:
        self._ensure_valid_token()
        resp = self._client.delete(f"/sandboxes/{project_id}")
        resp.raise_for_status()
        return resp.json()

    def status(self, project_id: str) -> dict[str, Any]:
        self._ensure_valid_token()
        resp = self._client.get(f"/sandboxes/{project_id}/status")
        resp.raise_for_status()
        return resp.json()

    def exec(self, project_id: str, command: str, *, timeout: int | None = None) -> dict[str, Any]:
        self._ensure_valid_token()
        body: dict[str, Any] = {"command": command}
        if timeout:
            body["timeout"] = timeout
        resp = self._client.post(f"/sandboxes/{project_id}/exec", json=body)
        resp.raise_for_status()
        return resp.json()

    def workflow(
        self,
        project_id: str,
        prompt: str,
        *,
        workflow_id: str | None = None,
        auto_approve: bool = False,
    ) -> dict[str, Any]:
        self._ensure_valid_token()
        body: dict[str, Any] = {"prompt": prompt}
        if workflow_id:
            body["workflowId"] = workflow_id
        if auto_approve:
            body["autoApprove"] = True
        resp = self._client.post(f"/sandboxes/{project_id}/workflow", json=body)
        resp.raise_for_status()
        return resp.json()

    def events(self, project_id: str, *, limit: int = 50) -> dict[str, Any]:
        self._ensure_valid_token()
        resp = self._client.get(f"/sandboxes/{project_id}/events", params={"limit": limit})
        resp.raise_for_status()
        return resp.json()

    def sessions(self, project_id: str) -> dict[str, Any]:
        self._ensure_valid_token()
        resp = self._client.get(f"/sandboxes/{project_id}/sessions")
        resp.raise_for_status()
        return resp.json()

    def export_session(self, project_id: str, session_id: str) -> dict[str, Any]:
        """Export a single session bundle from sandbox."""
        self._ensure_valid_token()
        resp = self._client.get(f"/sandboxes/{project_id}/sessions/{session_id}/export")
        resp.raise_for_status()
        return resp.json()

    def import_session(self, project_id: str, bundle: dict[str, Any]) -> dict[str, Any]:
        """Import a session bundle into sandbox."""
        self._ensure_valid_token()
        resp = self._client.post(f"/sandboxes/{project_id}/sessions/import", json=bundle)
        resp.raise_for_status()
        return resp.json()

    def git(self, project_id: str) -> dict[str, Any]:
        self._ensure_valid_token()
        resp = self._client.get(f"/sandboxes/{project_id}/git")
        resp.raise_for_status()
        return resp.json()

    def git_push(self, project_id: str) -> dict[str, Any]:
        self._ensure_valid_token()
        resp = self._client.post(f"/sandboxes/{project_id}/git/push")
        resp.raise_for_status()
        return resp.json()

    def export(self, project_id: str) -> dict[str, Any]:
        """Bulk-export all execution data from sandbox."""
        self._ensure_valid_token()
        resp = self._client.get(f"/sandboxes/{project_id}/export")
        resp.raise_for_status()
        return resp.json()

    def cancel_workflow(self, project_id: str) -> dict[str, Any]:
        """Cancel the running workflow in a sandbox."""
        self._ensure_valid_token()
        resp = self._client.post(f"/sandboxes/{project_id}/workflow/cancel")
        resp.raise_for_status()
        return resp.json()

    # -- SSE streaming methods ------------------------------------------------

    def _stream_sse(self, method: str, url: str, json_body: dict[str, Any]) -> Iterator[dict]:
        """Stream an SSE endpoint, yielding parsed JSON events.

        Iterates lines from the response. Lines prefixed with ``data: `` are
        parsed as JSON and yielded.  Empty lines, comment lines (starting with
        ``:``) and non-``data`` fields are silently skipped.  Connection and
        HTTP errors are caught so that callers receive an empty iterator
        instead of an exception.
        """
        try:
            with self._client.stream(method, url, json=json_body) as response:
                for line in response.iter_lines():
                    if not line or line.startswith(":"):
                        continue
                    if not line.startswith("data: "):
                        continue
                    payload = line[len("data: "):]
                    try:
                        yield json.loads(payload)
                    except (json.JSONDecodeError, ValueError):
                        logger.debug("Skipping malformed SSE payload: %s", payload)
                        continue
        except (httpx.HTTPStatusError, httpx.TransportError):
            # Connection refused, timeout, 5xx — degrade gracefully.
            return

    def exec_stream(self, project_id: str, command: str) -> Iterator[dict]:
        """Stream command execution via SSE."""
        self._ensure_valid_token()
        body: dict[str, Any] = {"command": command}
        yield from self._stream_sse(
            "POST",
            f"/sandboxes/{project_id}/exec/stream",
            json_body=body,
        )

    def workflow_stream(
        self,
        project_id: str,
        prompt: str,
        *,
        workflow: str | None = None,
        yes: bool = True,
    ) -> Iterator[dict]:
        """Stream workflow execution events via SSE."""
        self._ensure_valid_token()
        body: dict[str, Any] = {"prompt": prompt}
        if workflow:
            body["workflowId"] = workflow
        if yes:
            body["autoApprove"] = True
        yield from self._stream_sse(
            "POST",
            f"/sandboxes/{project_id}/workflow/stream",
            json_body=body,
        )


def get_sandbox_client() -> SandboxClient:
    """Create a SandboxClient from env vars or pixl config.

    Resolution order:
    1. PIXL_SANDBOX_URL / PIXL_SANDBOX_API_KEY / PIXL_SANDBOX_JWT_SECRET env vars
    2. pixl config get sandbox_url / sandbox_api_key / sandbox_jwt_secret

    When a JWT secret is available, a short-lived token is generated on the fly
    and used instead of the static API key.
    """
    url = os.environ.get("PIXL_SANDBOX_URL")
    key = os.environ.get("PIXL_SANDBOX_API_KEY")
    jwt_secret = os.environ.get("PIXL_SANDBOX_JWT_SECRET")

    if not url or (not key and not jwt_secret):
        try:
            from pathlib import Path

            from pixl.paths import canonical_project_root
            from pixl.storage.config_store import ConfigStore

            store = ConfigStore(canonical_project_root(Path.cwd()))
            if not url:
                url = store.get("sandbox_url")
            if not key:
                key = store.get("sandbox_api_key")
            if not jwt_secret:
                jwt_secret = store.get("sandbox_jwt_secret")
        except Exception:
            pass

    if not url:
        raise ValueError(
            "Sandbox URL not configured. "
            "Set PIXL_SANDBOX_URL env var or run: pixl config set sandbox_url <url>"
        )

    # Prefer JWT over static key
    if jwt_secret:
        return SandboxClient(url, "", jwt_secret=jwt_secret)
    elif not key:
        raise ValueError(
            "Sandbox auth not configured. "
            "Set PIXL_SANDBOX_JWT_SECRET (preferred) or PIXL_SANDBOX_API_KEY env var, "
            "or run: pixl config set sandbox_jwt_secret <secret>"
        )

    return SandboxClient(url, key)
