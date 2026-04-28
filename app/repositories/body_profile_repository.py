from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.body_profile import BodyProfile


class BodyProfileRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, data: dict) -> BodyProfile:
        profile = BodyProfile(user_id=user_id, **data)
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def get_by_id(self, profile_id: int) -> Optional[BodyProfile]:
        result = await self.db.execute(
            select(BodyProfile).where(
                BodyProfile.id == profile_id,
                BodyProfile.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int) -> Optional[BodyProfile]:
        result = await self.db.execute(
            select(BodyProfile)
            .where(
                BodyProfile.user_id == user_id,
                BodyProfile.is_deleted == False,
            )
            .order_by(BodyProfile.created_at.desc())
        )
        return result.scalars().first()

    async def get_by_beta_hash(self, beta_hash: str) -> Optional[BodyProfile]:
        result = await self.db.execute(
            select(BodyProfile).where(
                BodyProfile.beta_hash == beta_hash,
                BodyProfile.is_deleted == False,
            )
        )
        return result.scalars().first()

    async def update(self, profile_id: int, **kwargs) -> Optional[BodyProfile]:
        profile = await self.get_by_id(profile_id)
        if not profile:
            return None
        for field, value in kwargs.items():
            setattr(profile, field, value)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def update_beta_cache(
        self, profile_id: int, beta_cache: dict, beta_hash: str
    ) -> Optional[BodyProfile]:
        return await self.update(
            profile_id, beta_cache=beta_cache, beta_hash=beta_hash
        )

    async def soft_delete(self, profile_id: int) -> bool:
        profile = await self.get_by_id(profile_id)
        if not profile:
            return False
        profile.is_deleted = True
        await self.db.commit()
        return True
