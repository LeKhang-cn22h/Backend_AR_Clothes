from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User
from schemas.user import UserCreate, UserUpdate


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: UserCreate) -> User:
        user = User(**data.model_dump())
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_by_id(self, id: int) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == id, User.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def get_by_firebase_uid(self, firebase_uid: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.firebase_uid == firebase_uid, User.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.email == email, User.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 20) -> list[User]:
        result = await self.db.execute(
            select(User).where(User.is_deleted == False).offset(skip).limit(limit).order_by(User.id)
        )
        return list(result.scalars().all())

    async def update(self, id: int, data: UserUpdate) -> Optional[User]:
        user = await self.get_by_id(id)
        if not user:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete(self, id: int) -> bool:
        user = await self.get_by_id(id)
        if not user:
            return False
        user.is_deleted = True
        await self.db.commit()
        return True

    async def count(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(User).where(User.is_deleted == False)
        )
        return result.scalar_one()
