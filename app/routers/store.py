# -*- coding: utf-8 -*-
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from repositories.store_repository import StoreRepository
from schemas.store import StoreCreate, StoreResponse, StoreUpdate
from services.store_service import StoreService

router = APIRouter(prefix="/stores", tags=["stores"])


def get_store_service(db: AsyncSession = Depends(get_db)) -> StoreService:
    return StoreService(StoreRepository(db))


@router.post("", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
async def create_store(
    payload: StoreCreate,
    service: StoreService = Depends(get_store_service),
):
    return await service.create(payload)


@router.get("", response_model=list[StoreResponse])
async def list_stores(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    is_active: Optional[bool] = Query(default=None),
    service: StoreService = Depends(get_store_service),
):
    return await service.get_all(skip=skip, limit=limit, is_active=is_active)


@router.get("/{id}", response_model=StoreResponse)
async def get_store(
    id: uuid.UUID,
    service: StoreService = Depends(get_store_service),
):
    return await service.get_by_id(id)


@router.patch("/{id}", response_model=StoreResponse)
async def update_store(
    id: uuid.UUID,
    payload: StoreUpdate,
    service: StoreService = Depends(get_store_service),
):
    return await service.update(id, payload)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_store(
    id: uuid.UUID,
    service: StoreService = Depends(get_store_service),
):
    await service.delete(id)
