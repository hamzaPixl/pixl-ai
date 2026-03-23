"""Tests for scoped JWT tokens (T10) and token refresh (T11)."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from pixl_cli.sandbox_client import SandboxClient, _generate_jwt

# Test-only signing key (not a real secret)
_TEST_HMAC_KEY = "hmac-key-for-unit-tests-only"


# ---------------------------------------------------------------------------
# T10: Scoped JWT tokens
# ---------------------------------------------------------------------------


class TestGenerateJwtScope:
    """Verify _generate_jwt includes scope claim."""

    def test_default_scope_is_admin(self) -> None:
        token = _generate_jwt(_TEST_HMAC_KEY)
        import jwt

        payload = jwt.decode(
            token,
            _TEST_HMAC_KEY,
            algorithms=["HS256"],
            options={"verify_exp": False},
        )
        assert payload["scope"] == "admin"

    def test_custom_scope(self) -> None:
        token = _generate_jwt(_TEST_HMAC_KEY, scope="read")
        import jwt

        payload = jwt.decode(
            token,
            _TEST_HMAC_KEY,
            algorithms=["HS256"],
            options={"verify_exp": False},
        )
        assert payload["scope"] == "read"

    def test_write_scope(self) -> None:
        token = _generate_jwt(_TEST_HMAC_KEY, scope="write")
        import jwt

        payload = jwt.decode(
            token,
            _TEST_HMAC_KEY,
            algorithms=["HS256"],
            options={"verify_exp": False},
        )
        assert payload["scope"] == "write"

    def test_iss_claim_preserved(self) -> None:
        token = _generate_jwt(_TEST_HMAC_KEY, scope="read")
        import jwt

        payload = jwt.decode(
            token,
            _TEST_HMAC_KEY,
            algorithms=["HS256"],
            options={"verify_exp": False},
        )
        assert payload["iss"] == "pixl-cli"


class TestSandboxClientScope:
    """Verify SandboxClient stores scope."""

    def test_init_with_default_scope(self) -> None:
        client = SandboxClient("https://sandbox.example.com", "test-key")
        assert client._scope == "admin"

    def test_init_with_custom_scope(self) -> None:
        client = SandboxClient(
            "https://sandbox.example.com",
            "test-key",
            scope="read",
        )
        assert client._scope == "read"


# ---------------------------------------------------------------------------
# T11: Token refresh
# ---------------------------------------------------------------------------


class TestTokenRefresh:
    """Verify auto-refresh of JWT tokens before expiry."""

    def test_stores_token_generated_at(self) -> None:
        """SandboxClient with jwt_secret should record generation time."""
        before = datetime.now(UTC)
        client = SandboxClient(
            "https://sandbox.example.com",
            "initial-key",
            jwt_secret=_TEST_HMAC_KEY,
            expiry_minutes=60,
        )
        after = datetime.now(UTC)
        assert client._token_generated_at is not None
        assert before <= client._token_generated_at <= after

    def test_no_refresh_when_token_fresh(self) -> None:
        """Token within expiry window should not be refreshed."""
        client = SandboxClient(
            "https://sandbox.example.com",
            "initial-key",
            jwt_secret=_TEST_HMAC_KEY,
            expiry_minutes=60,
        )
        original_token = client._client.headers["authorization"]
        client._ensure_valid_token()
        assert client._client.headers["authorization"] == original_token

    def test_refresh_when_near_expiry(self) -> None:
        """Token within 5 minutes of expiry should be refreshed."""
        client = SandboxClient(
            "https://sandbox.example.com",
            "initial-key",
            jwt_secret=_TEST_HMAC_KEY,
            expiry_minutes=60,
        )
        # Simulate token generated 56 minutes ago (4 min until expiry)
        old_generated_at = datetime.now(UTC) - timedelta(minutes=56)
        client._token_generated_at = old_generated_at

        with patch(
            "pixl_cli.sandbox_client._generate_jwt",
            return_value="refreshed-token",
        ) as mock_gen:
            client._ensure_valid_token()

        mock_gen.assert_called_once_with(
            _TEST_HMAC_KEY,
            60,
            scope="admin",
        )
        assert client._client.headers["authorization"] == "Bearer refreshed-token"
        assert client._token_generated_at > old_generated_at

    def test_no_refresh_without_jwt_secret(self) -> None:
        """Client without jwt_secret should not attempt refresh."""
        client = SandboxClient(
            "https://sandbox.example.com",
            "static-api-key",
        )
        assert client._jwt_secret is None
        assert client._token_generated_at is None
        # Should not raise
        client._ensure_valid_token()

    def test_refresh_updates_generated_at(self) -> None:
        """After refresh, _token_generated_at should be updated."""
        client = SandboxClient(
            "https://sandbox.example.com",
            "initial-key",
            jwt_secret=_TEST_HMAC_KEY,
            expiry_minutes=60,
        )
        old_time = datetime.now(UTC) - timedelta(minutes=56)
        client._token_generated_at = old_time

        client._ensure_valid_token()

        assert client._token_generated_at > old_time

    def test_thread_safe_refresh(self) -> None:
        """Multiple threads should not corrupt state."""
        client = SandboxClient(
            "https://sandbox.example.com",
            "initial-key",
            jwt_secret=_TEST_HMAC_KEY,
            expiry_minutes=60,
        )
        # Force near-expiry
        client._token_generated_at = datetime.now(UTC) - timedelta(minutes=56)

        errors: list[Exception] = []

        def refresh() -> None:
            try:
                client._ensure_valid_token()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=refresh) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert client._token_generated_at is not None

    def test_ensure_valid_token_called_in_create(self) -> None:
        """HTTP methods should call _ensure_valid_token."""
        client = SandboxClient(
            "https://sandbox.example.com",
            "initial-key",
            jwt_secret=_TEST_HMAC_KEY,
            expiry_minutes=60,
        )
        with (
            patch.object(client, "_ensure_valid_token") as mock_ensure,
            patch.object(client._client, "post") as mock_post,
        ):
            mock_post.return_value = MagicMock(
                status_code=200,
                json=MagicMock(return_value={"status": "ready"}),
            )
            mock_post.return_value.raise_for_status = MagicMock()
            client.create("test-project")
            mock_ensure.assert_called_once()

    def test_ensure_valid_token_called_in_status(self) -> None:
        """status() should call _ensure_valid_token."""
        client = SandboxClient(
            "https://sandbox.example.com",
            "initial-key",
            jwt_secret=_TEST_HMAC_KEY,
            expiry_minutes=60,
        )
        with (
            patch.object(client, "_ensure_valid_token") as mock_ensure,
            patch.object(client._client, "get") as mock_get,
        ):
            mock_get.return_value = MagicMock(
                status_code=200,
                json=MagicMock(return_value={"status": "running"}),
            )
            mock_get.return_value.raise_for_status = MagicMock()
            client.status("test-project")
            mock_ensure.assert_called_once()

    def test_ensure_valid_token_called_in_destroy(self) -> None:
        """destroy() should call _ensure_valid_token."""
        client = SandboxClient(
            "https://sandbox.example.com",
            "initial-key",
            jwt_secret=_TEST_HMAC_KEY,
            expiry_minutes=60,
        )
        with (
            patch.object(client, "_ensure_valid_token") as mock_ensure,
            patch.object(client._client, "delete") as mock_delete,
        ):
            mock_delete.return_value = MagicMock(
                status_code=200,
                json=MagicMock(return_value={"success": True}),
            )
            mock_delete.return_value.raise_for_status = MagicMock()
            client.destroy("test-project")
            mock_ensure.assert_called_once()
