"""API error hierarchy and error handler registration."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# --- Error hierarchy ---


class APIError(Exception):
    """Base exception for all API errors."""

    status_code: int = 500
    detail: str = "Internal server error"
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, detail: str | None = None, **extra: Any) -> None:
        if detail is not None:
            self.detail = detail
        self.extra = extra
        super().__init__(self.detail)


class AuthenticationError(APIError):
    status_code = 401
    detail = "Not authenticated"
    error_code = "AUTHENTICATION_ERROR"


class AuthorizationError(APIError):
    status_code = 403
    detail = "Access denied"
    error_code = "AUTHORIZATION_ERROR"


class NotFoundError(APIError):
    status_code = 404
    detail = "Resource not found"
    error_code = "NOT_FOUND"


class ConflictError(APIError):
    status_code = 409
    detail = "Conflict"
    error_code = "CONFLICT"


class ValidationError(APIError):
    status_code = 422
    detail = "Validation error"
    error_code = "VALIDATION_ERROR"


class BusinessLogicError(APIError):
    status_code = 400
    detail = "Business logic error"
    error_code = "BUSINESS_LOGIC_ERROR"


# --- Error response builder ---


def _error_response(
    status_code: int,
    message: str,
    code: str,
    request_id: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        },
    )


# --- Handler registration ---


def register_error_handlers(app: FastAPI) -> None:
    """Register exception handlers for APIError and a catch-all middleware."""

    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        logger.warning(
            "API error [%s]: %s (path=%s, request_id=%s)",
            exc.status_code,
            exc.detail,
            request.url.path,
            request_id,
        )
        return _error_response(exc.status_code, exc.detail, exc.error_code, request_id)

    @app.middleware("http")
    async def catch_unhandled_errors(request: Request, call_next: Any) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
            logger.exception(
                "Unhandled exception (path=%s, request_id=%s): %s",
                request.url.path,
                request_id,
                exc,
            )
            return _error_response(
                500, "An unexpected error occurred", "INTERNAL_ERROR", request_id
            )
