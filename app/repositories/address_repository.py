from typing import Optional
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from models.address import Address
from schemas.address import AddressCreate, AddressUpdate


class AddressRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, data: AddressCreate) -> Address:
        address = Address(user_id=user_id, **data.model_dump())
        self.db.add(address)
        await self.db.commit()
        await self.db.refresh(address)
        return address

    async def get_by_id(self, id: int) -> Optional[Address]:
        result = await self.db.execute(select(Address).where(Address.id == id))
        return result.scalar_one_or_none()

    async def get_all_by_user(self, user_id: int) -> list[Address]:
        result = await self.db.execute(
            select(Address).where(Address.user_id == user_id).order_by(Address.id)
        )
        return list(result.scalars().all())

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Address]:
        result = await self.db.execute(select(Address).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def update(self, id: int, data: AddressUpdate) -> Optional[Address]:
        address = await self.get_by_id(id)
        if not address:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(address, field, value)
        await self.db.commit()
        await self.db.refresh(address)
        return address

    async def delete(self, id: int) -> bool:
        address = await self.get_by_id(id)
        if not address:
            return False
        await self.db.delete(address)
        await self.db.commit()
        return True

    async def clear_default_for_user(self, user_id: int) -> None:
        await self.db.execute(
            update(Address).where(Address.user_id == user_id).values(is_default=False)
        )
        await self.db.commit()

    async def count(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(Address))
        return result.scalar_one()
