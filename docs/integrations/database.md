# Async Database Integration

This template ships with an async SQLAlchemy integration that demonstrates how to
wire database connections, dependencies, and routes end-to-end. The goal is to
provide a working reference that can be adapted to your own domain models.

## What you get

- `AppSettings` entries for configuring the async engine (URL, pool size, echo)
- A reusable integration module that initialises the engine/sessionmaker during
  application startup and disposes them on shutdown
- FastAPI dependencies that yield `AsyncSession` instances with automatic
  cleanup
- A miniature domain (`ExampleItem`) with a service layer showcasing async CRUD
- Demo API routes under `/api/v1/examples/database-example`
- Integration tests that exercise the full stack using an in-memory SQLite
  database

## Configuration

The integration is configured via environment variables surfaced in
`.env.example`:

```ini
APP_DATABASE_URL=sqlite+aiosqlite:///./app.db
APP_DATABASE_POOL_SIZE=5
APP_DATABASE_ECHO=false
```

Update these values in your `.env` file to point at your preferred database.
The URL must use an async driver (e.g. `postgresql+asyncpg://`). Pool size is
applied for non-SQLite backends, while SQLite receives sensible defaults and
in-memory connections automatically share state using a `StaticPool`.

## Lifespan management

`src/app/core/lifespan.py` coordinates database startup and shutdown:

```python
engine = await init_database(settings)
await create_example_schema(engine)
```

On shutdown the engine is disposed, ensuring connections are returned to the
pool. The schema helper runs once per boot so your demo tables exist before
requests are served. Replace `create_example_schema` with your own metadata
initialisation once you have real migrations in place.

## Working with sessions

Two dependency providers are available:

- `get_async_sessionmaker()` – returns the configured
  `async_sessionmaker[AsyncSession]`
- `get_async_session()` – yields an `AsyncSession` inside an async context

Use them in routes or background workers:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_async_session
from app.services import ExampleItemService

@router.post("/items")
async def create_item(
    payload: ExampleItemCreate,
    session: AsyncSession = Depends(get_async_session),
):
    service = ExampleItemService(session)
    item = await service.create_item(payload)
    return ExampleItemRead.model_validate(item)
```

## Example domain

`src/app/services/database_example.py` contains a lightweight SQLAlchemy ORM
model (`ExampleItem`) and service class. The service performs async SELECT and
INSERT operations, commits transactions, and returns ORM instances. The API
layer serialises them into Pydantic response models.

Try the demo endpoints once the server is running:

- `GET  /api/v1/examples/database-example/` – list items
- `POST /api/v1/examples/database-example/` – create a new item
- `GET  /api/v1/examples/database-example/{item_id}` – fetch a single item

## Testing

`tests/integrations/test_database.py` demonstrates how to run async tests using
the shared `async_client` fixture. The fixture bootstraps an in-memory SQLite
database so tests remain isolated and fast. Assertions cover schema creation,
dependency behaviour, and CRUD flows through the HTTP layer.

Use these tests as a template for your own repositories and services.

