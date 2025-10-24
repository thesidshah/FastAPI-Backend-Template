from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Declarative base for SQLAlchemy ORM models.

    All domain models in this example inherit from this base. In a real
    application, you would define your own Base class with common functionality
    like created_at/updated_at timestamps, soft deletes, etc.
    """


class ExampleItem(Base):
    """
    Example SQLAlchemy ORM model demonstrating async database integration.

    This is a minimal model used for demonstration purposes. Replace with your
    own domain models in production.

    Attributes:
        id: Auto-incrementing primary key
        name: Item name (required)
        description: Optional item description
    """

    __tablename__ = "example_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column()
    description: Mapped[str | None]


class ExampleItemCreate(BaseModel):
    """
    Pydantic schema for creating a new ExampleItem.

    Used for request validation in POST endpoints.
    """

    name: str
    description: str | None = None


class ExampleItemRead(BaseModel):
    """
    Pydantic schema for reading/returning ExampleItem data.

    Configured with from_attributes=True to support conversion from
    SQLAlchemy ORM models.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None


class ExampleItemService:
    """
    Service layer for ExampleItem CRUD operations.

    Encapsulates database logic for the ExampleItem domain model. This pattern
    keeps route handlers thin and makes business logic testable in isolation.

    Args:
        session: AsyncSession instance injected via dependency injection
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_items(self) -> Sequence[ExampleItem]:
        """
        Retrieve all items ordered by ID.

        Returns:
            Sequence of ExampleItem instances
        """
        result = await self._session.execute(
            select(ExampleItem).order_by(ExampleItem.id),
        )
        return result.scalars().all()

    async def create_item(self, payload: ExampleItemCreate) -> ExampleItem:
        """
        Create a new item and persist to database.

        Args:
            payload: Validated creation data

        Returns:
            The newly created ExampleItem instance with ID populated
        """
        item = ExampleItem(name=payload.name, description=payload.description)
        self._session.add(item)
        await self._session.commit()
        await self._session.refresh(item)  # Load auto-generated fields
        return item

    async def get_item(self, item_id: int) -> ExampleItem | None:
        """
        Retrieve a single item by ID.

        Args:
            item_id: Primary key of the item to retrieve

        Returns:
            ExampleItem if found, None otherwise
        """
        result = await self._session.execute(
            select(ExampleItem).where(ExampleItem.id == item_id),
        )
        return result.scalar_one_or_none()


async def create_example_schema(engine: AsyncEngine) -> None:
    """
    Create database tables for the example domain.

    Uses SQLAlchemy's create_all() to create tables. In production, use a
    migration tool like Alembic instead.

    Args:
        engine: AsyncEngine instance to use for schema creation

    Example:
        >>> engine = await init_database(settings)
        >>> await create_example_schema(engine)
    """
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
