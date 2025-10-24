from __future__ import annotations

from typing import Any

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from ..core.config import AppSettings

# Module-level singletons for the async engine and sessionmaker.
# These are initialized once during application startup via init_database()
# and disposed on shutdown via shutdown_database().
_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _build_engine_kwargs(settings: AppSettings) -> dict[str, Any]:
    """
    Build keyword arguments for SQLAlchemy's create_async_engine.

    Configures database-specific settings:
    - SQLite: Uses StaticPool for in-memory databases to share state across
      connections, disables same-thread check for async compatibility
    - Other databases (PostgreSQL, MySQL, etc.): Configures connection pooling
      with pool_pre_ping for connection health checks

    Args:
        settings: Application settings containing database configuration

    Returns:
        Dictionary of engine kwargs to pass to create_async_engine()
    """
    url = make_url(settings.database_url)
    kwargs: dict[str, Any] = {
        "echo": settings.database_echo,
    }

    if url.get_backend_name() == "sqlite":
        # Share the in-memory database across connections when requested.
        # This is essential for testing with in-memory SQLite databases.
        if url.database in {":memory:", None} or (
            isinstance(url.database, str) and url.database.startswith("file::memory:")
        ):
            kwargs["poolclass"] = StaticPool
        # SQLite doesn't support same-thread check in async contexts
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # For production databases (PostgreSQL, MySQL, etc.)
        kwargs["pool_size"] = settings.database_pool_size
        # Enable connection health checks before using from pool
        kwargs["pool_pre_ping"] = True

    return kwargs


def get_engine() -> AsyncEngine:
    """
    Return the initialized async database engine.

    Raises:
        RuntimeError: If init_database() has not been called yet

    Returns:
        The configured AsyncEngine instance
    """
    if _engine is None:  # pragma: no cover - defensive guard
        raise RuntimeError(
            "Database engine has not been initialised. "
            "Ensure init_database() is called during application startup.",
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """
    Return the configured async session factory.

    Raises:
        RuntimeError: If init_database() has not been called yet

    Returns:
        The configured async_sessionmaker[AsyncSession] instance
    """
    if _sessionmaker is None:  # pragma: no cover - defensive guard
        raise RuntimeError(
            "Database sessionmaker has not been initialised. "
            "Ensure init_database() is called during application startup.",
        )
    return _sessionmaker


async def init_database(settings: AppSettings) -> AsyncEngine:
    """
    Initialize the async database engine and session factory.

    This function is idempotent - it will only create the engine once even if
    called multiple times. Should be called during application startup in the
    lifespan handler.

    Args:
        settings: Application settings containing database configuration

    Returns:
        The initialized AsyncEngine instance

    Example:
        >>> from app.core.config import AppSettings
        >>> settings = AppSettings()
        >>> engine = await init_database(settings)
    """
    global _engine, _sessionmaker

    if _engine is None:
        engine_kwargs = _build_engine_kwargs(settings)
        _engine = create_async_engine(settings.database_url, **engine_kwargs)
        # expire_on_commit=False prevents lazy-loading errors after commit
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)

    return get_engine()


async def shutdown_database() -> None:
    """
    Dispose of the async engine and reset module state.

    Properly closes all database connections and releases resources. Should be
    called during application shutdown in the lifespan handler.

    This function is safe to call even if init_database() was never called.

    Example:
        >>> await shutdown_database()
    """
    global _engine, _sessionmaker

    if _engine is not None:
        # Close all connections in the pool
        await _engine.dispose()

    # Reset module state for clean shutdown/testing
    _engine = None
    _sessionmaker = None
