"""Tests for foundation.auth.secret — JWT secret management."""

from __future__ import annotations

from pathlib import Path

import pytest
from pixl_api.foundation.auth.secret import get_jwt_secret


class TestGetJwtSecret:
    def test_returns_env_var_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PIXL_JWT_SECRET", "my-env-secret")
        assert get_jwt_secret() == "my-env-secret"

    def test_generates_file_when_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("PIXL_JWT_SECRET", raising=False)
        secret_path = tmp_path / ".pixl" / "jwt_secret"
        monkeypatch.setattr(
            "pixl_api.foundation.auth.secret._secret_file_path", lambda: secret_path
        )

        secret = get_jwt_secret()
        assert len(secret) > 32
        assert secret_path.exists()
        # File should have restrictive permissions
        mode = secret_path.stat().st_mode & 0o777
        assert mode == 0o600

    def test_reads_existing_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PIXL_JWT_SECRET", raising=False)
        secret_path = tmp_path / ".pixl" / "jwt_secret"
        secret_path.parent.mkdir(parents=True)
        secret_path.write_text("stored-secret")
        secret_path.chmod(0o600)
        monkeypatch.setattr(
            "pixl_api.foundation.auth.secret._secret_file_path", lambda: secret_path
        )

        assert get_jwt_secret() == "stored-secret"

    def test_fixes_insecure_permissions(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("PIXL_JWT_SECRET", raising=False)
        secret_path = tmp_path / ".pixl" / "jwt_secret"
        secret_path.parent.mkdir(parents=True)
        secret_path.write_text("stored-secret")
        secret_path.chmod(0o644)  # insecure
        monkeypatch.setattr(
            "pixl_api.foundation.auth.secret._secret_file_path", lambda: secret_path
        )

        get_jwt_secret()
        mode = secret_path.stat().st_mode & 0o777
        assert mode == 0o600
