"""API configuration via environment variables."""

from __future__ import annotations

import os

API_PORT = int(os.getenv("PIXL_API_PORT", "8420"))
CORS_ORIGINS = os.getenv("PIXL_CORS_ORIGINS", "http://localhost:5173").split(",")
LOG_LEVEL = os.getenv("PIXL_LOG_LEVEL", "INFO").upper()
