"""Tests for foundation.api.errors — error hierarchy and middleware."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pixl_api.foundation.api.errors import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    BusinessLogicError,
    ConflictError,
    NotFoundError,
    ValidationError,
    register_error_handlers,
)


class TestErrorHierarchy:
    def test_api_error_defaults(self) -> None:
        err = APIError()
        assert err.status_code == 500
        assert err.error_code == "INTERNAL_ERROR"

    def test_custom_detail(self) -> None:
        err = NotFoundError("Widget not found")
        assert err.detail == "Widget not found"
        assert err.status_code == 404

    def test_authentication_error(self) -> None:
        err = AuthenticationError()
        assert err.status_code == 401
        assert err.error_code == "AUTHENTICATION_ERROR"

    def test_authorization_error(self) -> None:
        err = AuthorizationError()
        assert err.status_code == 403
        assert err.error_code == "AUTHORIZATION_ERROR"

    def test_conflict_error(self) -> None:
        err = ConflictError()
        assert err.status_code == 409

    def test_validation_error(self) -> None:
        err = ValidationError()
        assert err.status_code == 422

    def test_business_logic_error(self) -> None:
        err = BusinessLogicError("Bad input")
        assert err.status_code == 400
        assert err.detail == "Bad input"

    def test_all_are_api_errors(self) -> None:
        for cls in [
            AuthenticationError,
            AuthorizationError,
            NotFoundError,
            ConflictError,
            ValidationError,
            BusinessLogicError,
        ]:
            assert issubclass(cls, APIError)


@pytest.mark.asyncio
class TestErrorHandlerMiddleware:
    async def test_catches_api_error(self) -> None:
        app = FastAPI()
        register_error_handlers(app)

        @app.get("/fail")
        async def fail():
            raise NotFoundError("Thing not found")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/fail")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "NOT_FOUND"
        assert body["error"]["message"] == "Thing not found"

    async def test_catches_unhandled_exception(self) -> None:
        app = FastAPI()
        register_error_handlers(app)

        @app.get("/boom")
        async def boom():
            raise RuntimeError("unexpected")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/boom")
        assert resp.status_code == 500
        body = resp.json()
        assert body["error"]["code"] == "INTERNAL_ERROR"
