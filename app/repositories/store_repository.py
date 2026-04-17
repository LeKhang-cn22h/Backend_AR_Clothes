# -*- coding: utf-8 -*-
import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.store import Store
from schemas.store import StoreCreate, StoreUpdate


class StoreRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, store_create: StoreCreate) -> Store:
        store = Store(**store_create.model_dump())
        self.db.add(store)
        await self.db.commit()
        await self.db.refresh(store)
        return store

    async def get_by_id(self, id: uuid.UUID) -> Optional[Store]:
        result = await self.db.execute(select(Store).where(Store.id == id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Store]:
        result = await self.db.execute(select(Store).where(Store.email == email))
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 10,
        is_active: Optional[bool] = None,
    ) -> list[Store]:
        query = select(Store)
        if is_active is not None:
            query = query.where(Store.is_active == is_active)
        query = query.offset(skip).limit(limit).order_by(Store.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(self, id: uuid.UUID, store_update: StoreUpdate) -> Optional[Store]:
        store = await self.get_by_id(id)
        if not store:
            return None
        data = store_update.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(store, field, value)
        await self.db.commit()
        await self.db.refresh(store)
        return store

    async def delete(self, id: uuid.UUID) -> bool:
        store = await self.get_by_id(id)
        if not store:
            return False
        await self.db.delete(store)
        await self.db.commit()
        return True

    async def count(self, is_active: Optional[bool] = None) -> int:
        query = select(func.count()).select_from(Store)
        if is_active is not None:
            query = query.where(Store.is_active == is_active)
        result = await self.db.execute(query)
        return result.scalar_one()
