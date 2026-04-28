from typing import Optional

from fastapi import HTTPException

from models.photo_avatar import PhotoAvatar
from repositories.body_profile_repository import BodyProfileRepository
from repositories.photo_avatar_repository import PhotoAvatarRepository
from repositories.user_repository import UserRepository


class PhotoAvatarService:
    def __init__(
        self,
        repo: PhotoAvatarRepository,
        user_repo: UserRepository,
        body_profile_repo: BodyProfileRepository,
    ):
        self.repo = repo
        self.user_repo = user_repo
        self.body_profile_repo = body_profile_repo

    async def create_avatar_job(
        self, user_id: int, body_profile_id: Optional[int] = None
    ) -> PhotoAvatar:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Khong tim thay user")

        if body_profile_id is not None:
            profile = await self.body_profile_repo.get_by_id(body_profile_id)
            if not profile:
                raise HTTPException(
                    status_code=404, detail="Khong tim thay body profile"
                )
            if profile.user_id != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Body profile khong thuoc ve user nay",
                )

        return await self.repo.create(
            user_id=user_id, body_profile_id=body_profile_id
        )

    async def get_avatar(
        self, avatar_id: int, user_id: int
    ) -> Optional[PhotoAvatar]:
        avatar = await self.repo.get_by_id(avatar_id)
        if not avatar:
            return None
        if avatar.user_id != user_id:
            raise HTTPException(
                status_code=403, detail="Avatar khong thuoc ve user nay"
            )
        return avatar
