from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..integrations.database import get_sessionmaker


def get_async_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """
    FastAPI dependency that returns the async session factory.

    Use this when you need direct access to the sessionmaker, for example when
    creating sessions in background tasks or testing utilities.

    Returns:
        The configured async_sessionmaker[AsyncSession] instance

    Example:
        >>> from fastapi import Depends
        >>> def my_route(sessionmaker = Depends(get_async_sessionmaker)):
        >>>     async with sessionmaker() as session:
        >>>         # Use session...
        >>>         pass
    """
    return get_sessionmaker()


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """
    FastAPI dependency that yields an AsyncSession with automatic cleanup.

    The session is automatically committed on success and rolled back on
    exceptions. Always closed when the request completes. This is the
    recommended way to use database sessions in route handlers.

    Yields:
        An AsyncSession instance bound to the current request

    Example:
        >>> from fastapi import Depends
        >>> from sqlalchemy.ext.asyncio import AsyncSession
        >>>
        >>> @router.get("/users")
        >>> async def list_users(session: AsyncSession = Depends(get_async_session)):
        >>>     result = await session.execute(select(User))
        >>>     return result.scalars().all()
    """
    session_factory = get_async_sessionmaker()
    async with session_factory() as session:
        yield session
