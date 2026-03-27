"""FastAPI application factory for the pixl API."""

from __future__ import annotations

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from pixl_api.config import CORS_ORIGINS, LOG_LEVEL
from pixl_api.foundation.api.errors import register_error_handlers
from pixl_api.foundation.config.security import get_cors_config

try:
    from scalar_fastapi import get_scalar_api_reference
except ImportError:
    get_scalar_api_reference = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(levelname)-8s %(name)s — %(message)s",
        stream=sys.stderr,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Startup
        from pixl_api.db import init_db
        from pixl_api.pool import project_pool

        init_db()
        app.state.pool = project_pool
        logger.info("pixl API started")
        yield
        # Shutdown
        project_pool.close_all()
        logger.info("pixl API shutdown complete")

    app = FastAPI(
        title="pixl API",
        description="REST API for pixl project management and workflow execution",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )

    # CORS
    cors_config = get_cors_config(CORS_ORIGINS)
    app.add_middleware(CORSMiddleware, **cors_config)

    # Error handlers
    register_error_handlers(app)

    # Scalar API docs (replaces Swagger UI)
    if get_scalar_api_reference is not None:

        @app.get("/docs", include_in_schema=False)
        async def scalar_docs() -> JSONResponse:
            return get_scalar_api_reference(
                openapi_url=app.openapi_url,
                title=app.title,
            )

    # Routes
    from pixl_api.routes import get_api_routers

    for router in get_api_routers():
        app.include_router(router, prefix="/api")

    # Health check
    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
