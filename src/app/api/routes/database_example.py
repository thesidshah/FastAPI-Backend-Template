from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...dependencies import get_async_session
from ...services import ExampleItemCreate, ExampleItemRead, ExampleItemService

router = APIRouter(prefix="/database-example", tags=["Database Example"])


def get_example_service(
    session: AsyncSession = Depends(get_async_session),
) -> ExampleItemService:
    """
    FastAPI dependency that provides an ExampleItemService instance.

    The service is initialized with an async database session that will be
    automatically cleaned up after the request completes.

    Args:
        session: AsyncSession injected via get_async_session dependency

    Returns:
        Initialized ExampleItemService instance
    """
    return ExampleItemService(session)


@router.get("/", response_model=list[ExampleItemRead])
async def list_example_items(
    service: ExampleItemService = Depends(get_example_service),
) -> list[ExampleItemRead]:
    """
    List all example items.

    Returns all items ordered by ID. This demonstrates basic async database
    query patterns with SQLAlchemy.

    Args:
        service: Injected ExampleItemService instance

    Returns:
        List of ExampleItemRead schemas
    """
    items = await service.list_items()
    return [ExampleItemRead.model_validate(item) for item in items]


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ExampleItemRead,
)
async def create_example_item(
    payload: ExampleItemCreate,
    service: ExampleItemService = Depends(get_example_service),
) -> ExampleItemRead:
    """
    Create a new example item.

    Demonstrates async INSERT operations with automatic transaction management
    via the session dependency.

    Args:
        payload: Validated item creation data
        service: Injected ExampleItemService instance

    Returns:
        The created item with generated ID
    """
    item = await service.create_item(payload)
    return ExampleItemRead.model_validate(item)


@router.get("/{item_id}", response_model=ExampleItemRead)
async def get_example_item(
    item_id: int,
    service: ExampleItemService = Depends(get_example_service),
) -> ExampleItemRead:
    """
    Retrieve a single example item by ID.

    Returns 404 if the item doesn't exist. Demonstrates async SELECT queries
    and proper error handling.

    Args:
        item_id: Primary key of the item to retrieve
        service: Injected ExampleItemService instance

    Returns:
        The requested item

    Raises:
        HTTPException: 404 if item not found
    """
    item = await service.get_item(item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found",
        )
    return ExampleItemRead.model_validate(item)
