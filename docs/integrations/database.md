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

## Production considerations

### Database migrations

The example uses `create_all()` for simplicity, but production applications should
use a proper migration tool. We recommend [Alembic](https://alembic.sqlalchemy.org/):

```bash
# Install Alembic
uv pip install alembic

# Initialize Alembic
alembic init alembic

# Create a migration
alembic revision --autogenerate -m "Add users table"

# Apply migrations
alembic upgrade head
```

Update your lifespan handler to run migrations instead of `create_all()`:

```python
# src/app/core/lifespan.py
from alembic import command
from alembic.config import Config

async def startup():
    engine = await init_database(settings)

    # Run migrations synchronously
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
```

### Connection pooling

For production databases (PostgreSQL, MySQL), configure appropriate pool settings:

```ini
# .env
APP_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname
APP_DATABASE_POOL_SIZE=10
APP_DATABASE_MAX_OVERFLOW=20
APP_DATABASE_POOL_TIMEOUT=30
APP_DATABASE_POOL_RECYCLE=3600
```

Add these fields to `AppSettings`:

```python
database_max_overflow: int = Field(default=20, ge=0)
database_pool_timeout: int = Field(default=30, ge=1)
database_pool_recycle: int = Field(default=3600, ge=-1)
```

### Error handling

Wrap database operations in try-except blocks to handle connection errors gracefully:

```python
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status

@router.post("/items")
async def create_item(payload: ExampleItemCreate, service: ExampleItemService = Depends(get_example_service)):
    try:
        item = await service.create_item(payload)
        return ExampleItemRead.model_validate(item)
    except SQLAlchemyError as e:
        logger.error("database.error", error=str(e), operation="create_item")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed"
        )
```

### Read replicas

For high-traffic applications, use read replicas for queries:

```python
# src/app/integrations/database.py
_read_engine: AsyncEngine | None = None

async def init_database(settings: AppSettings) -> AsyncEngine:
    global _engine, _read_engine, _sessionmaker

    if _engine is None:
        # Primary (write) engine
        _engine = create_async_engine(settings.database_url, **engine_kwargs)

        # Read replica engine (if configured)
        if settings.database_read_replica_url:
            _read_engine = create_async_engine(
                settings.database_read_replica_url,
                **engine_kwargs
            )

        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)

    return _engine
```

## Best practices

### 1. Use dependency injection

Always inject sessions through FastAPI dependencies rather than creating them directly:

```python
# Good
async def my_route(session: AsyncSession = Depends(get_async_session)):
    ...

# Avoid
async def my_route():
    async with get_async_sessionmaker()() as session:
        ...
```

### 2. Keep business logic in services

Separate database operations from route handlers:

```python
# Good - testable service layer
class UserService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_user(self, data: UserCreate) -> User:
        user = User(**data.model_dump())
        self._session.add(user)
        await self._session.commit()
        return user

# Route is thin
@router.post("/users")
async def create_user(data: UserCreate, service: UserService = Depends()):
    return await service.create_user(data)
```

### 3. Use explicit transactions

For complex operations, use explicit transaction control:

```python
async def transfer_funds(from_id: int, to_id: int, amount: Decimal, session: AsyncSession):
    async with session.begin_nested():  # Savepoint
        from_account = await session.get(Account, from_id)
        to_account = await session.get(Account, to_id)

        from_account.balance -= amount
        to_account.balance += amount

        await session.flush()  # Validate constraints before commit
```

### 4. Optimize queries

Use eager loading to avoid N+1 queries:

```python
from sqlalchemy.orm import selectinload

# Avoid N+1 queries
stmt = select(User).options(selectinload(User.posts))
result = await session.execute(stmt)
users = result.scalars().all()
```

### 5. Index frequently queried columns

Add indexes to your models for better performance:

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(index=True)
```

## Supported databases

The async integration supports any database with an async driver:

| Database   | Driver Package      | URL Example                              |
|------------|---------------------|------------------------------------------|
| PostgreSQL | `asyncpg`           | `postgresql+asyncpg://user:pass@host/db` |
| MySQL      | `aiomysql`          | `mysql+aiomysql://user:pass@host/db`     |
| SQLite     | `aiosqlite`         | `sqlite+aiosqlite:///./app.db`           |
| Oracle     | `oracledb` (async)  | `oracle+oracledb_async://user:pass@dsn` |

Install the appropriate driver:

```bash
# PostgreSQL
uv pip install asyncpg

# MySQL
uv pip install aiomysql

# SQLite (already included)
uv pip install aiosqlite
```

## Troubleshooting

### "Event loop is closed" errors

Ensure you're using async session methods and not mixing sync/async code:

```python
# Wrong - sync query method
result = session.execute(stmt)

# Correct - async query method
result = await session.execute(stmt)
```

### Connection pool exhausted

If you see "TimeoutError: QueuePool limit of size X overflow Y reached", increase pool size:

```ini
APP_DATABASE_POOL_SIZE=20
APP_DATABASE_MAX_OVERFLOW=40
```

Or check for leaked sessions (ensure all sessions are properly closed via dependency injection).

### Schema not created

Verify your lifespan handler is being called. Check logs for:

```
INFO     app.startup lifespan=startup
```

If missing, ensure `create_app()` properly installs the lifespan handler.

## Additional resources

- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [SQLAlchemy async ORM](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic Migrations](https://alembic.sqlalchemy.org/en/latest/)
- [FastAPI SQL Databases](https://fastapi.tiangolo.com/tutorial/sql-databases/)

