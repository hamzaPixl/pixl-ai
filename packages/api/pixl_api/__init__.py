"""pixl API — thin FastAPI layer over pixl-cli."""

from __future__ import annotations


def create_app():  # noqa: ANN201
    """FastAPI application factory."""
    from pixl_api.app import create_app as _create

    return _create()
