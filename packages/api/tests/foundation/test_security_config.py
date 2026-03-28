"""Tests for foundation.config.security."""

from __future__ import annotations

import logging

import pytest
from pixl_api.foundation.config.security import get_cors_config, validate_jwt_secret


class TestGetCorsConfig:
    def test_returns_dict_with_origins(self) -> None:
        config = get_cors_config(["http://localhost:3000"])
        assert config["allow_origins"] == ["http://localhost:3000"]
        assert config["allow_credentials"] is True
        assert config["allow_methods"] == ["*"]
        assert config["allow_headers"] == ["*"]

    def test_multiple_origins(self) -> None:
        origins = ["http://localhost:3000", "https://app.example.com"]
        config = get_cors_config(origins)
        assert config["allow_origins"] == origins


class TestValidateJwtSecret:
    def test_warns_on_short_secret(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            validate_jwt_secret("short")
        assert "too short" in caplog.text.lower() or "at least" in caplog.text.lower()

    def test_no_warning_on_strong_secret(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            validate_jwt_secret("a" * 32)
        assert caplog.text == ""
