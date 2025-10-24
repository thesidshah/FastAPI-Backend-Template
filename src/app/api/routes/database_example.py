from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...dependencies import get_async_session
from ...services import ExampleItemCreate, ExampleItemRead, ExampleItemService

router = APIRouter(prefix="/database-example", tags=["Database Example"])


def get_example_service(
    session: AsyncSession = Depends(get_async_session),
) -> ExampleItemService:
    return ExampleItemService(session)


@router.get("/", response_model=list[ExampleItemRead])
async def list_example_items(
    service: ExampleItemService = Depends(get_example_service),
) -> list[ExampleItemRead]:
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
    item = await service.create_item(payload)
    return ExampleItemRead.model_validate(item)


@router.get("/{item_id}", response_model=ExampleItemRead)
async def get_example_item(
    item_id: int,
    service: ExampleItemService = Depends(get_example_service),
) -> ExampleItemRead:
    item = await service.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return ExampleItemRead.model_validate(item)

