from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from models.body_profile import BodyProfile
from repositories.body_profile_repository import BodyProfileRepository
from repositories.user_repository import UserRepository
from schemas.body_profile import BodyProfileCreate


class BodyProfileService:
    def __init__(
        self,
        repo: BodyProfileRepository,
        user_repo: UserRepository,
    ):
        self.repo = repo
        self.user_repo = user_repo

    async def get_by_user_id(self, user_id: int) -> BodyProfile | None:
        return await self.repo.get_by_user_id(user_id)

    async def create_or_update_profile(
        self, user_id: int, data: BodyProfileCreate
    ) -> BodyProfile:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Không tìm thấy user")

        payload = data.model_dump()

        existing = await self.repo.get_by_user_id(user_id)
        if existing:
            return await self.repo.update(existing.id, **payload)

        return await self.repo.create(user_id=user_id, data=payload)

    async def delete_profile(self, profile_id: int) -> bool:
        return await self.repo.soft_delete(profile_id)