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

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _build_engine_kwargs(settings: AppSettings) -> dict[str, Any]:
    """Return keyword arguments for the async engine based on configuration."""

    url = make_url(settings.database_url)
    kwargs: dict[str, Any] = {
        "echo": settings.database_echo,
    }

    if url.get_backend_name() == "sqlite":
        # Share the in-memory database across connections when requested.
        if url.database in {":memory:", None} or (
            isinstance(url.database, str) and url.database.startswith("file::memory:")
        ):
            kwargs["poolclass"] = StaticPool
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = settings.database_pool_size
        kwargs["pool_pre_ping"] = True

    return kwargs


def get_engine() -> AsyncEngine:
    """Return the initialised async engine or raise if unavailable."""

    if _engine is None:  # pragma: no cover - defensive guard
        raise RuntimeError("Database engine has not been initialised")
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the configured async sessionmaker."""

    if _sessionmaker is None:  # pragma: no cover - defensive guard
        raise RuntimeError("Database sessionmaker has not been initialised")
    return _sessionmaker


async def init_database(settings: AppSettings) -> AsyncEngine:
    """Initialise the async engine and session factory."""

    global _engine, _sessionmaker

    if _engine is None:
        engine_kwargs = _build_engine_kwargs(settings)
        _engine = create_async_engine(settings.database_url, **engine_kwargs)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)

    return get_engine()


async def shutdown_database() -> None:
    """Dispose of the async engine and reset integration state."""

    global _engine, _sessionmaker

    if _engine is not None:
        await _engine.dispose()

    _engine = None
    _sessionmaker = None

