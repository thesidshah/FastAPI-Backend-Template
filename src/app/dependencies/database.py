from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..integrations.database import get_sessionmaker


def get_async_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Expose the configured async session factory for dependency injection."""

    return get_sessionmaker()


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Yield an `AsyncSession` with proper cleanup semantics."""

    session_factory = get_async_sessionmaker()
    async with session_factory() as session:
        yield session

