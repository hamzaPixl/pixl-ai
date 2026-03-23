"""Integration tests for SandboxClient.

Covers JWT generation, auth headers, HTTP method routing, SSE streaming
parser, error handling, and the get_sandbox_client() factory.
"""

from __future__ import annotations

import base64
import json
import os
import time
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pixl_cli.sandbox_client import SandboxClient, _generate_jwt, get_sandbox_client

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client() -> SandboxClient:
    """Return a SandboxClient pointed at a fake base URL."""
    return SandboxClient("https://sandbox.example.com", "test-api-key")


@pytest.fixture()
def jwt_secret() -> str:
    return "super-secret-256bit-key-for-testing"


# ---------------------------------------------------------------------------
# JWT generation
# ---------------------------------------------------------------------------


class TestGenerateJWT:
    """Verify _generate_jwt produces well-formed JWTs with correct claims."""

    def test_returns_three_part_token(self, jwt_secret: str) -> None:
        token = _generate_jwt(jwt_secret)
        parts = token.split(".")
        assert len(parts) == 3, "JWT must have header.payload.signature"

    def test_header_specifies_hs256(self, jwt_secret: str) -> None:
        token = _generate_jwt(jwt_secret)
        header_b64 = token.split(".")[0]
        # Add padding if needed
        padded = header_b64 + "=" * (-len(header_b64) % 4)
        header = json.loads(base64.urlsafe_b64decode(padded))
        assert header["alg"] == "HS256"
        assert header["typ"] == "JWT"

    def test_payload_contains_required_claims(self, jwt_secret: str) -> None:
        token = _generate_jwt(jwt_secret)
        payload_b64 = token.split(".")[1]
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))

        assert payload["iss"] == "pixl-cli"
        assert "iat" in payload
        assert "exp" in payload

    def test_expiry_defaults_to_one_hour(self, jwt_secret: str) -> None:
        token = _generate_jwt(jwt_secret)
        payload_b64 = token.split(".")[1]
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))

        diff = payload["exp"] - payload["iat"]
        assert diff == 60 * 60, f"Expected 3600s expiry, got {diff}s"

    def test_custom_expiry_minutes(self, jwt_secret: str) -> None:
        token = _generate_jwt(jwt_secret, expiry_minutes=15)
        payload_b64 = token.split(".")[1]
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))

        diff = payload["exp"] - payload["iat"]
        assert diff == 15 * 60

    def test_can_be_verified_with_pyjwt(self, jwt_secret: str) -> None:
        import jwt

        token = _generate_jwt(jwt_secret)
        decoded = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        assert decoded["iss"] == "pixl-cli"
        assert decoded["exp"] > time.time()

    def test_raises_import_error_without_pyjwt(self, jwt_secret: str) -> None:
        """When PyJWT is not installed, a clear ImportError is raised."""
        with patch.dict("sys.modules", {"jwt": None}):
            with pytest.raises(ImportError, match="PyJWT is required"):
                _generate_jwt(jwt_secret)


# ---------------------------------------------------------------------------
# Auth header
# ---------------------------------------------------------------------------


class TestAuthHeader:
    """Verify the Authorization header is set correctly."""

    def test_uses_bearer_token_from_api_key(self) -> None:
        client = SandboxClient("https://sb.example.com", "my-static-key")
        assert client._client.headers["authorization"] == "Bearer my-static-key"

    def test_uses_jwt_when_jwt_secret_provided(self, jwt_secret: str) -> None:
        """get_sandbox_client should generate a JWT and pass it as api_key."""
        env = {
            "PIXL_SANDBOX_URL": "https://sb.example.com",
            "PIXL_SANDBOX_JWT_SECRET": jwt_secret,
        }
        with patch.dict(os.environ, env, clear=False):
            # Remove the static key so it doesn't short-circuit
            os.environ.pop("PIXL_SANDBOX_API_KEY", None)
            sb = get_sandbox_client()

        auth = sb._client.headers["authorization"]
        assert auth.startswith("Bearer ")
        token = auth.split(" ", 1)[1]
        # Must be a valid JWT (three parts)
        assert len(token.split(".")) == 3
        sb.close()

    def test_static_key_over_jwt_when_no_secret(self) -> None:
        env = {
            "PIXL_SANDBOX_URL": "https://sb.example.com",
            "PIXL_SANDBOX_API_KEY": "static-key-123",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("PIXL_SANDBOX_JWT_SECRET", None)
            sb = get_sandbox_client()

        assert sb._client.headers["authorization"] == "Bearer static-key-123"
        sb.close()


# ---------------------------------------------------------------------------
# HTTP method routing
# ---------------------------------------------------------------------------


class TestHTTPMethods:
    """Verify each client method calls the correct URL and HTTP method."""

    def test_create_posts_to_sandboxes(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "proj-1"}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "post", return_value=mock_resp) as mock_post:
            result = client.create("proj-1")

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "/sandboxes"
        assert call_args[1]["json"]["projectId"] == "proj-1"
        assert result == {"id": "proj-1"}

    def test_create_forwards_env_vars(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "proj-1"}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "post", return_value=mock_resp) as mock_post:
            client.create("proj-1", env_vars={"MY_VAR": "hello"})

        body = mock_post.call_args[1]["json"]
        assert body["envVars"]["MY_VAR"] == "hello"

    def test_create_includes_repo_and_branch(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "proj-1"}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "post", return_value=mock_resp) as mock_post:
            client.create("proj-1", repo_url="https://github.com/x/y", branch="dev")

        body = mock_post.call_args[1]["json"]
        assert body["repoUrl"] == "https://github.com/x/y"
        assert body["branch"] == "dev"

    def test_destroy_deletes_sandbox(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"deleted": True}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "delete", return_value=mock_resp) as mock_del:
            result = client.destroy("proj-1")

        mock_del.assert_called_once_with("/sandboxes/proj-1")
        assert result == {"deleted": True}

    def test_status_gets_sandbox_status(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"state": "running"}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "get", return_value=mock_resp) as mock_get:
            result = client.status("proj-1")

        mock_get.assert_called_once_with("/sandboxes/proj-1/status")
        assert result["state"] == "running"

    def test_workflow_posts_prompt(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "post", return_value=mock_resp) as mock_post:
            result = client.workflow("proj-1", "build a landing page")

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "/sandboxes/proj-1/workflow"
        body = call_args[1]["json"]
        assert body["prompt"] == "build a landing page"
        assert result["success"] is True

    def test_workflow_includes_optional_params(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "post", return_value=mock_resp) as mock_post:
            client.workflow("proj-1", "deploy", workflow_id="wf-1", auto_approve=True)

        body = mock_post.call_args[1]["json"]
        assert body["workflowId"] == "wf-1"
        assert body["autoApprove"] is True

    def test_events_gets_with_limit(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"events": []}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "get", return_value=mock_resp) as mock_get:
            result = client.events("proj-1", limit=25)

        mock_get.assert_called_once_with("/sandboxes/proj-1/events", params={"limit": 25})
        assert result == {"events": []}

    def test_sessions_gets_sandbox_sessions(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"sessions": ["s1", "s2"]}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "get", return_value=mock_resp) as mock_get:
            result = client.sessions("proj-1")

        mock_get.assert_called_once_with("/sandboxes/proj-1/sessions")
        assert result == {"sessions": ["s1", "s2"]}

    def test_exec_posts_command(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"stdout": "hello"}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "post", return_value=mock_resp) as mock_post:
            result = client.exec("proj-1", "echo hello")

        call_args = mock_post.call_args
        assert call_args[0][0] == "/sandboxes/proj-1/exec"
        assert call_args[1]["json"]["command"] == "echo hello"
        assert result["stdout"] == "hello"

    def test_exec_includes_timeout(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"stdout": "ok"}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "post", return_value=mock_resp) as mock_post:
            client.exec("proj-1", "sleep 5", timeout=10)

        body = mock_post.call_args[1]["json"]
        assert body["timeout"] == 10

    def test_export_session_gets_correct_url(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"bundle": {}}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "get", return_value=mock_resp) as mock_get:
            client.export_session("proj-1", "sess-42")

        mock_get.assert_called_once_with("/sandboxes/proj-1/sessions/sess-42/export")

    def test_import_session_posts_bundle(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"imported": True}
        mock_resp.raise_for_status = MagicMock()

        bundle = {"session": {"id": "sess-1"}, "events": []}
        with patch.object(client._client, "post", return_value=mock_resp) as mock_post:
            client.import_session("proj-1", bundle)

        call_args = mock_post.call_args
        assert call_args[0][0] == "/sandboxes/proj-1/sessions/import"
        assert call_args[1]["json"] == bundle

    def test_git_gets_status(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"branch": "main"}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "get", return_value=mock_resp) as mock_get:
            result = client.git("proj-1")

        mock_get.assert_called_once_with("/sandboxes/proj-1/git")
        assert result["branch"] == "main"

    def test_git_push_posts(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"pushed": True}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "post", return_value=mock_resp) as mock_post:
            client.git_push("proj-1")

        mock_post.assert_called_once_with("/sandboxes/proj-1/git/push")

    def test_export_gets_bulk_data(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": []}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "get", return_value=mock_resp) as mock_get:
            client.export("proj-1")

        mock_get.assert_called_once_with("/sandboxes/proj-1/export")

    def test_cancel_workflow_posts(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"cancelled": True}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "post", return_value=mock_resp) as mock_post:
            client.cancel_workflow("proj-1")

        mock_post.assert_called_once_with("/sandboxes/proj-1/workflow/cancel")


# ---------------------------------------------------------------------------
# SSE streaming
# ---------------------------------------------------------------------------


def _make_stream_response(lines: list[str]) -> MagicMock:
    """Build a mock httpx response that yields lines from iter_lines()."""
    mock_resp = MagicMock()
    mock_resp.iter_lines.return_value = iter(lines)
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestStreamSSE:
    """Verify _stream_sse parses SSE protocol correctly."""

    def test_parses_data_lines(self, client: SandboxClient) -> None:
        lines = [
            'data: {"type":"log","msg":"hi"}',
            "",
            'data: {"type":"done"}',
        ]
        mock_resp = _make_stream_response(lines)
        with patch.object(client._client, "stream", return_value=mock_resp):
            events = list(client._stream_sse("POST", "/test", {}))

        assert len(events) == 2
        assert events[0] == {"type": "log", "msg": "hi"}
        assert events[1] == {"type": "done"}

    def test_skips_comments_and_empty_lines(self, client: SandboxClient) -> None:
        lines = ["", ": keepalive", "", 'data: {"ok":true}', ""]
        mock_resp = _make_stream_response(lines)
        with patch.object(client._client, "stream", return_value=mock_resp):
            events = list(client._stream_sse("POST", "/test", {}))

        assert events == [{"ok": True}]

    def test_skips_non_data_fields(self, client: SandboxClient) -> None:
        lines = ["event: update", "id: 99", 'data: {"v":1}']
        mock_resp = _make_stream_response(lines)
        with patch.object(client._client, "stream", return_value=mock_resp):
            events = list(client._stream_sse("POST", "/test", {}))

        assert events == [{"v": 1}]

    def test_skips_malformed_json_gracefully(self, client: SandboxClient) -> None:
        lines = ["data: {broken", 'data: {"valid":true}']
        mock_resp = _make_stream_response(lines)
        with patch.object(client._client, "stream", return_value=mock_resp):
            events = list(client._stream_sse("POST", "/test", {}))

        assert events == [{"valid": True}]


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Verify HTTP errors are raised or handled as expected."""

    def test_4xx_raises_http_status_error(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )

        with patch.object(client._client, "get", return_value=mock_resp):
            with pytest.raises(httpx.HTTPStatusError):
                client.status("nonexistent")

    def test_5xx_raises_http_status_error(self, client: SandboxClient) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

        with patch.object(client._client, "post", return_value=mock_resp):
            with pytest.raises(httpx.HTTPStatusError):
                client.create("proj-1")

    def test_stream_connection_error_yields_empty(self, client: SandboxClient) -> None:
        with patch.object(client._client, "stream", side_effect=httpx.ConnectError("refused")):
            events = list(client._stream_sse("POST", "/test", {}))

        assert events == []

    def test_stream_timeout_yields_empty(self, client: SandboxClient) -> None:
        with patch.object(client._client, "stream", side_effect=httpx.TimeoutException("timeout")):
            events = list(client._stream_sse("POST", "/test", {}))

        assert events == []

    def test_stream_http_error_yields_empty(self, client: SandboxClient) -> None:
        with patch.object(
            client._client,
            "stream",
            side_effect=httpx.HTTPStatusError(
                "502", request=MagicMock(), response=MagicMock(status_code=502)
            ),
        ):
            events = list(client._stream_sse("POST", "/test", {}))

        assert events == []


# ---------------------------------------------------------------------------
# get_sandbox_client factory
# ---------------------------------------------------------------------------


class TestGetSandboxClient:
    """Verify get_sandbox_client resolves config from env vars and falls back to config store."""

    def test_resolves_from_env_vars(self) -> None:
        env = {
            "PIXL_SANDBOX_URL": "https://sb.example.com",
            "PIXL_SANDBOX_API_KEY": "env-key",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("PIXL_SANDBOX_JWT_SECRET", None)
            sb = get_sandbox_client()

        assert sb._client.headers["authorization"] == "Bearer env-key"
        sb.close()

    def test_prefers_jwt_secret_over_api_key(self) -> None:
        env = {
            "PIXL_SANDBOX_URL": "https://sb.example.com",
            "PIXL_SANDBOX_API_KEY": "static-key",
            "PIXL_SANDBOX_JWT_SECRET": "jwt-secret-test",
        }
        with patch.dict(os.environ, env, clear=False):
            sb = get_sandbox_client()

        auth = sb._client.headers["authorization"]
        # Should be a JWT, not the static key
        token = auth.replace("Bearer ", "")
        assert len(token.split(".")) == 3
        assert token != "static-key"
        sb.close()

    def test_raises_when_no_url(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            # Force the config store import to fail so the fallback is a no-op
            with patch.dict("sys.modules", {"pixl.paths": None, "pixl.storage.config_store": None}):
                with pytest.raises(ValueError, match="Sandbox URL not configured"):
                    get_sandbox_client()

    def test_raises_when_no_auth(self) -> None:
        env = {"PIXL_SANDBOX_URL": "https://sb.example.com"}
        with patch.dict(os.environ, env, clear=True):
            # Force the config store import to fail
            with patch.dict("sys.modules", {"pixl.paths": None, "pixl.storage.config_store": None}):
                with pytest.raises(ValueError, match="Sandbox auth not configured"):
                    get_sandbox_client()

    def test_falls_back_to_config_store(self) -> None:
        """When env vars are missing, get_sandbox_client tries ConfigStore."""
        mock_store = MagicMock()
        mock_store.get.side_effect = lambda k: {
            "sandbox_url": "https://config-sb.example.com",
            "sandbox_api_key": "config-key",
            "sandbox_jwt_secret": None,
        }.get(k)

        mock_config_module = MagicMock()
        mock_config_module.ConfigStore.return_value = mock_store
        mock_paths_module = MagicMock()
        mock_paths_module.canonical_project_root.return_value = "/tmp"

        with patch.dict(os.environ, {}, clear=True):
            with patch.dict(
                "sys.modules",
                {
                    "pixl.storage.config_store": mock_config_module,
                    "pixl.paths": mock_paths_module,
                },
            ):
                sb = get_sandbox_client()

        assert sb._client.headers["authorization"] == "Bearer config-key"
        sb.close()

    def test_base_url_trailing_slash_stripped(self) -> None:
        sb = SandboxClient("https://sb.example.com/", "key")
        assert str(sb._client.base_url).rstrip("/") == "https://sb.example.com"
        sb.close()


# ---------------------------------------------------------------------------
# Client lifecycle
# ---------------------------------------------------------------------------


class TestClientLifecycle:
    """Verify client setup and teardown."""

    def test_timeout_set_to_300(self) -> None:
        sb = SandboxClient("https://sb.example.com", "key")
        assert sb._client.timeout.read == 300.0
        sb.close()

    def test_close_closes_underlying_client(self) -> None:
        sb = SandboxClient("https://sb.example.com", "key")
        with patch.object(sb._client, "close") as mock_close:
            sb.close()
        mock_close.assert_called_once()
