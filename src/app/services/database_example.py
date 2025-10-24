from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for the demo models."""


class ExampleItem(Base):
    """Simple example model used for database integration demos."""

    __tablename__ = "example_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column()
    description: Mapped[str | None]


class ExampleItemCreate(BaseModel):
    name: str
    description: str | None = None


class ExampleItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None


class ExampleItemService:
    """Provide CRUD style helpers for the example model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_items(self) -> Sequence[ExampleItem]:
        result = await self._session.execute(
            select(ExampleItem).order_by(ExampleItem.id)
        )
        return result.scalars().all()

    async def create_item(self, payload: ExampleItemCreate) -> ExampleItem:
        item = ExampleItem(name=payload.name, description=payload.description)
        self._session.add(item)
        await self._session.commit()
        await self._session.refresh(item)
        return item

    async def get_item(self, item_id: int) -> ExampleItem | None:
        result = await self._session.execute(
            select(ExampleItem).where(ExampleItem.id == item_id)
        )
        return result.scalar_one_or_none()


async def create_example_schema(engine: AsyncEngine) -> None:
    """Create database tables for the demo domain."""

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

