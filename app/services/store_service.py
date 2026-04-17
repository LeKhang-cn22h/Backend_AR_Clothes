# -*- coding: utf-8 -*-
import uuid
from typing import Optional

from fastapi import HTTPException

from repositories.store_repository import StoreRepository
from models.store import Store
from schemas.store import StoreCreate, StoreUpdate


class StoreService:
    def __init__(self, repo: StoreRepository):
        self.repo = repo

    async def create(self, store_create: StoreCreate) -> Store:
        if store_create.email:
            existing = await self.repo.get_by_email(store_create.email)
            if existing:
                raise HTTPException(status_code=409, detail="Email da duoc su dung boi cua hang khac")
        return await self.repo.create(store_create)

    async def get_by_id(self, id: uuid.UUID) -> Store:
        store = await self.repo.get_by_id(id)
        if not store:
            raise HTTPException(status_code=404, detail="Khong tim thay cua hang")
        return store

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 10,
        is_active: Optional[bool] = None,
    ) -> list[Store]:
        return await self.repo.get_all(skip=skip, limit=limit, is_active=is_active)

    async def update(self, id: uuid.UUID, store_update: StoreUpdate) -> Store:
        if store_update.email:
            existing = await self.repo.get_by_email(store_update.email)
            if existing and existing.id != id:
                raise HTTPException(status_code=409, detail="Email da duoc su dung boi cua hang khac")
        store = await self.repo.update(id, store_update)
        if not store:
            raise HTTPException(status_code=404, detail="Khong tim thay cua hang")
        return store

    async def delete(self, id: uuid.UUID) -> None:
        deleted = await self.repo.delete(id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Khong tim thay cua hang")
