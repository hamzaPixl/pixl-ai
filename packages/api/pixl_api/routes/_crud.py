"""Generic CRUD router factory for backlog entities.

Generates the standard 9 routes (list, create, get, put, patch, delete,
transition, history, transitions) from a declarative configuration,
eliminating duplication across features/epics/roadmaps routes.

Implementation note: endpoints are built via ``exec()`` so that FastAPI
can introspect dynamically-named path and query parameters.  The
``from __future__ import annotations`` import is intentionally omitted
to keep annotation resolution eager -- required for exec-generated
functions consumed by FastAPI.
"""

import asyncio
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from pixl_api.deps import ProjectDB
from pixl_api.errors import EntityNotFoundError, InvalidTransitionError
from pixl_api.helpers import get_or_404
from pixl_api.schemas.features import TransitionRequest


@dataclass(frozen=True)
class FilterParam:
    """Describes an extra Query parameter for the list endpoint."""

    name: str
    description: str = ""


def make_crud_router(
    *,
    prefix: str,
    tag: str,
    entity_name: str,
    entity_id_param: str,
    list_method: str,
    get_method: str,
    create_method: str,
    update_method: str,
    remove_method: str,
    create_schema: type[BaseModel],
    update_schema: type[BaseModel],
    list_filters: list[FilterParam] | None = None,
    paginate: bool = True,
) -> APIRouter:
    """Build an APIRouter with standard CRUD + transition + history.

    Parameters
    ----------
    prefix:
        URL prefix, e.g. ``"/projects/{project_id}/features"``.
    tag:
        OpenAPI tag name.
    entity_name:
        Singular name for error messages (e.g. ``"feature"``).
    entity_id_param:
        Path parameter name (e.g. ``"feature_id"``).
    list_method:
        Method name on ``db.backlog`` for listing.
    get_method:
        Method name on ``db.backlog`` for single-entity fetch.
    create_method:
        Method name on ``db.backlog`` for creation.
    update_method:
        Method name on ``db.backlog`` for update.
    remove_method:
        Method name on ``db.backlog`` for deletion.
    create_schema:
        Pydantic model for the create request body.
    update_schema:
        Pydantic model for the update request body.
    list_filters:
        Extra Query parameters for the list endpoint.
    paginate:
        Add ``limit``/``offset`` with client-side slicing.
    """
    router = APIRouter(prefix=prefix, tags=[tag])
    filters = list_filters or []

    # Shared namespace for all exec-generated functions.
    ns: dict[str, Any] = {
        "asyncio": asyncio,
        "Any": Any,
        "Query": Query,
        "ProjectDB": ProjectDB,
        "get_or_404": get_or_404,
        "TransitionRequest": TransitionRequest,
        "InvalidTransitionError": InvalidTransitionError,
        "EntityNotFoundError": EntityNotFoundError,
        "create_schema": create_schema,
        "update_schema": update_schema,
    }

    _add_list(router, ns, entity_name, list_method, filters, paginate)
    _add_create(router, ns, entity_name, create_method)
    _add_get(router, ns, entity_name, entity_id_param, get_method)
    _add_update(router, ns, entity_name, entity_id_param, get_method, update_method)
    _add_delete(router, ns, entity_name, entity_id_param, get_method, remove_method)
    _add_transition(router, ns, entity_name, entity_id_param, get_method)
    _add_history(router, ns, entity_name, entity_id_param)
    _add_transitions(router, ns, entity_name, entity_id_param)

    return router


# ---------------------------------------------------------------------------
# Private endpoint builders
# ---------------------------------------------------------------------------


def _exec_and_register(
    router: APIRouter,
    ns: dict[str, Any],
    func_name: str,
    func_src: str,
    path: str,
    methods: list[str],
    *,
    status_code: int | None = None,
) -> None:
    """Execute *func_src* and add the function to *router*."""
    exec(func_src, ns)  # noqa: S102
    handler = ns[func_name]
    kwargs: dict[str, Any] = {}
    if status_code is not None:
        kwargs["status_code"] = status_code
    for method in methods:
        router.add_api_route(path, handler, methods=[method], **kwargs)


def _get_call(method: str, id_param: str) -> str:
    """Return a ``getattr(db.backlog, ...)`` call snippet."""
    return f"getattr(db.backlog, {method!r}), {id_param}"


# -- LIST ------------------------------------------------------------------


def _add_list(
    router: APIRouter,
    ns: dict[str, Any],
    entity_name: str,
    list_method: str,
    filters: list[FilterParam],
    paginate: bool,
) -> None:
    filter_names = [f.name for f in filters]

    param_lines: list[str] = [
        '    status: str | None = Query(None, description="Filter by status"),',
    ]
    for fp in filters:
        desc = fp.description or f"Filter by {fp.name}"
        param_lines.append(f'    {fp.name}: str | None = Query(None, description="{desc}"),')
    if paginate:
        param_lines.append('    limit: int = Query(50, ge=1, le=200, description="Max results"),')
        param_lines.append('    offset: int = Query(0, ge=0, description="Offset for pagination"),')

    params_str = "\n".join(param_lines)
    kw = ", ".join(f"{n}={n}" for n in ["status", *filter_names])

    if paginate:
        body = (
            "    results = await asyncio.to_thread(\n"
            f"        getattr(db.backlog, {list_method!r}),\n"
            f"        {kw},\n"
            "    )\n"
            "    return results[offset : offset + limit]"
        )
    else:
        body = (
            "    return await asyncio.to_thread(\n"
            f"        getattr(db.backlog, {list_method!r}),\n"
            f"        {kw},\n"
            "    )"
        )

    fn = f"list_{entity_name}s"
    src = (
        f"async def {fn}(\n"
        f"    db: ProjectDB,\n"
        f"{params_str}\n"
        f") -> list[dict[str, Any]]:\n"
        f'    """List {entity_name}s with optional filters."""\n'
        f"{body}\n"
    )
    _exec_and_register(router, ns, fn, src, "", ["GET"])


# -- CREATE ----------------------------------------------------------------


def _add_create(
    router: APIRouter,
    ns: dict[str, Any],
    entity_name: str,
    create_method: str,
) -> None:
    fn = f"create_{entity_name}"
    cm = create_method
    src = (
        f"async def {fn}(\n"
        "    db: ProjectDB,\n"
        "    body: create_schema,\n"
        ") -> dict[str, Any]:\n"
        f'    """Create a new {entity_name}."""\n'
        "    fields = body.model_dump(exclude_none=True)\n"
        "    fn = getattr(db.backlog, "
        f"{cm!r})\n"
        "    return await asyncio.to_thread(fn, **fields)\n"
    )
    _exec_and_register(router, ns, fn, src, "", ["POST"], status_code=201)


# -- GET -------------------------------------------------------------------


def _add_get(
    router: APIRouter,
    ns: dict[str, Any],
    entity_name: str,
    entity_id_param: str,
    get_method: str,
) -> None:
    fn = f"get_{entity_name}"
    gm = get_method
    ip = entity_id_param
    en = entity_name
    src = (
        f"async def {fn}(\n"
        "    db: ProjectDB,\n"
        f"    {ip}: str,\n"
        ") -> dict[str, Any]:\n"
        f'    """Get a single {en} by ID."""\n'
        f"    _get = getattr(db.backlog, {gm!r})\n"
        f"    result = await asyncio.to_thread(_get, {ip})\n"
        f"    return get_or_404(result, {en!r}, {ip})\n"
    )
    _exec_and_register(router, ns, fn, src, f"/{{{ip}}}", ["GET"])


# -- UPDATE (PUT + PATCH) --------------------------------------------------


def _add_update(
    router: APIRouter,
    ns: dict[str, Any],
    entity_name: str,
    entity_id_param: str,
    get_method: str,
    update_method: str,
) -> None:
    fn = f"update_{entity_name}"
    gm = get_method
    um = update_method
    ip = entity_id_param
    en = entity_name
    src = (
        f"async def {fn}(\n"
        "    db: ProjectDB,\n"
        f"    {ip}: str,\n"
        "    body: update_schema,\n"
        ") -> dict[str, Any]:\n"
        f'    """Update an existing {en}."""\n'
        f"    _get = getattr(db.backlog, {gm!r})\n"
        f"    existing = await asyncio.to_thread(_get, {ip})\n"
        f"    get_or_404(existing, {en!r}, {ip})\n"
        "    fields = body.model_dump(exclude_none=True)\n"
        "    if fields:\n"
        f"        _upd = getattr(db.backlog, {um!r})\n"
        f"        await asyncio.to_thread(_upd, {ip}, **fields)\n"
        f"    updated = await asyncio.to_thread(_get, {ip})\n"
        f"    return get_or_404(updated, {en!r}, {ip})\n"
    )
    _exec_and_register(router, ns, fn, src, f"/{{{ip}}}", ["PUT", "PATCH"])


# -- DELETE ----------------------------------------------------------------


def _add_delete(
    router: APIRouter,
    ns: dict[str, Any],
    entity_name: str,
    entity_id_param: str,
    get_method: str,
    remove_method: str,
) -> None:
    fn = f"delete_{entity_name}"
    gm = get_method
    rm = remove_method
    ip = entity_id_param
    en = entity_name
    src = (
        f"async def {fn}(\n"
        "    db: ProjectDB,\n"
        f"    {ip}: str,\n"
        ") -> dict[str, bool]:\n"
        f'    """Delete a {en}."""\n'
        f"    _get = getattr(db.backlog, {gm!r})\n"
        f"    existing = await asyncio.to_thread(_get, {ip})\n"
        f"    get_or_404(existing, {en!r}, {ip})\n"
        f"    _rm = getattr(db.backlog, {rm!r})\n"
        f"    await asyncio.to_thread(_rm, {ip})\n"
        '    return {"deleted": True}\n'
    )
    _exec_and_register(router, ns, fn, src, f"/{{{ip}}}", ["DELETE"])


# -- TRANSITION ------------------------------------------------------------


def _add_transition(
    router: APIRouter,
    ns: dict[str, Any],
    entity_name: str,
    entity_id_param: str,
    get_method: str,
) -> None:
    sm = f"update_{entity_name}_status"
    fn = f"transition_{entity_name}"
    gm = get_method
    ip = entity_id_param
    en = entity_name
    src = (
        f"async def {fn}(\n"
        "    db: ProjectDB,\n"
        f"    {ip}: str,\n"
        "    body: TransitionRequest,\n"
        ") -> dict[str, Any]:\n"
        f'    """Transition a {en} to a new status."""\n'
        f"    _get = getattr(db.backlog, {gm!r})\n"
        f"    entity = await asyncio.to_thread(_get, {ip})\n"
        f"    get_or_404(entity, {en!r}, {ip})\n"
        '    old_status = entity["status"]\n'
        "    try:\n"
        "        from pixl.state.engine import TransitionEngine\n"
        "        engine = TransitionEngine.default(db.backlog)\n"
        "        result = await asyncio.to_thread(\n"
        f"            engine.transition, {ip},\n"
        "            body.to_status, note=body.reason,\n"
        "        )\n"
        "        if not result.success:\n"
        "            raise InvalidTransitionError(\n"
        f"                {en!r}, {ip},\n"
        "                result.error or 'Transition not allowed',\n"
        "            )\n"
        "        return {\n"
        '            "old_status": old_status,\n'
        '            "new_status": body.to_status,\n'
        "        }\n"
        "    except ImportError:\n"
        f"        _st = getattr(db.backlog, {sm!r})\n"
        "        updated = await asyncio.to_thread(\n"
        f"            _st, {ip}, body.to_status,\n"
        "            note=body.reason,\n"
        "        )\n"
        "        if updated is None:\n"
        f"            raise EntityNotFoundError({en!r}, {ip})\n"
        "        return {\n"
        '            "old_status": old_status,\n'
        '            "new_status": body.to_status,\n'
        "        }\n"
    )
    _exec_and_register(
        router,
        ns,
        fn,
        src,
        f"/{{{ip}}}/transition",
        ["POST"],
    )


# -- HISTORY ---------------------------------------------------------------


def _add_history(
    router: APIRouter,
    ns: dict[str, Any],
    entity_name: str,
    entity_id_param: str,
) -> None:
    fn = f"{entity_name}_history"
    ip = entity_id_param
    en = entity_name
    src = (
        f"async def {fn}(\n"
        "    db: ProjectDB,\n"
        f"    {ip}: str,\n"
        ") -> list[dict[str, Any]]:\n"
        f'    """Get state transition history for a {en}."""\n'
        "    return await asyncio.to_thread(\n"
        f"        db.events.get_entity_history, {ip},\n"
        "    )\n"
    )
    _exec_and_register(router, ns, fn, src, f"/{{{ip}}}/history", ["GET"])


# -- TRANSITIONS -----------------------------------------------------------


def _add_transitions(
    router: APIRouter,
    ns: dict[str, Any],
    entity_name: str,
    entity_id_param: str,
) -> None:
    fn = f"{entity_name}_transitions"
    ip = entity_id_param
    en = entity_name
    src = (
        f"async def {fn}(\n"
        "    db: ProjectDB,\n"
        f"    {ip}: str,\n"
        ") -> list[dict[str, Any]]:\n"
        f'    """Get state transitions for a {en}."""\n'
        "    return await asyncio.to_thread(\n"
        f"        db.events.get_history, {en!r}, {ip},\n"
        "    )\n"
    )
    _exec_and_register(router, ns, fn, src, f"/{{{ip}}}/transitions", ["GET"])
