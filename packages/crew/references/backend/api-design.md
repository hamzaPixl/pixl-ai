# API Design Patterns

## RESTful Conventions

### URL Structure
- `GET /resources` — List (paginated)
- `GET /resources/:id` — Get single
- `POST /resources` — Create
- `PATCH /resources/:id` — Partial update
- `DELETE /resources/:id` — Delete (soft)

### Response Format
```json
// Single resource
{ "data": { ... } }

// List with pagination
{ "data": [...], "meta": { "total": 100, "limit": 20, "offset": 0 } }

// Error
{ "error": { "code": "NOT_FOUND", "message": "Resource not found" } }
```

### HTTP Status Codes
- `200` — Success
- `201` — Created
- `204` — Deleted (no content)
- `400` — Validation error
- `401` — Unauthenticated
- `403` — Forbidden (insufficient permissions)
- `404` — Not found
- `409` — Conflict
- `429` — Rate limited
- `500` — Internal server error

## Fastify Route Pattern

Every route in our SaaS services follows:
1. Permission guard as `preHandler`
2. `requireAuth()` to verify JWT
3. `withRequestContext()` to set actor context
4. Zod schema validation of request body/params/query
5. Domain logic (entity creation/update)
6. `unitOfWork.execute()` for mutations
7. Transform to response with `toResponse()`

## Python / FastAPI Route Pattern

For Python codebases (detected via `pyproject.toml`):

1. `APIRouter` with `prefix` and `tags`
2. Dependency injection via `Depends()`
3. Pydantic models for request/response validation
4. `HTTPException` for errors → `{"detail": "..."}` response
5. `BackgroundTasks` for async side effects
6. `*Store` classes for persistence (not Prisma)

```python
@router.get("/resources")
async def list_resources(limit: int = 20, offset: int = 0) -> dict:
    items = store.list(limit=limit, offset=offset)
    return {"data": [i.to_dict() for i in items], "meta": {"total": store.count(), "limit": limit, "offset": offset}}

@router.post("/resources", status_code=201)
async def create_resource(body: CreateRequest) -> dict:
    resource = Resource(**body.model_dump())
    store.save(resource)
    return {"data": resource.to_dict()}
```

## Pagination

- Use `limit` + `offset` query params
- Default limit: 20, max: 100
- Return `meta.total` for client-side pagination UI
