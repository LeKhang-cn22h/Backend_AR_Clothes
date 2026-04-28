from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.photo_avatar import PhotoAvatar


class PhotoAvatarRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, user_id: int, body_profile_id: Optional[int] = None
    ) -> PhotoAvatar:
        avatar = PhotoAvatar(
            user_id=user_id,
            body_profile_id=body_profile_id,
            status="processing",
        )
        self.db.add(avatar)
        await self.db.commit()
        await self.db.refresh(avatar)
        return avatar

    async def get_by_id(self, avatar_id: int) -> Optional[PhotoAvatar]:
        result = await self.db.execute(
            select(PhotoAvatar).where(
                PhotoAvatar.id == avatar_id,
                PhotoAvatar.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int) -> list[PhotoAvatar]:
        result = await self.db.execute(
            select(PhotoAvatar)
            .where(
                PhotoAvatar.user_id == user_id,
                PhotoAvatar.is_deleted == False,
            )
            .order_by(PhotoAvatar.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        avatar_id: int,
        status: str,
        error_message: Optional[str] = None,
    ) -> Optional[PhotoAvatar]:
        avatar = await self.get_by_id(avatar_id)
        if not avatar:
            return None
        avatar.status = status
        if error_message is not None:
            avatar.error_message = error_message
        await self.db.commit()
        await self.db.refresh(avatar)
        return avatar

    async def update_urls(
        self,
        avatar_id: int,
        head_glb_url: Optional[str] = None,
        body_glb_url: Optional[str] = None,
        merged_glb_url: Optional[str] = None,
        neck_joint: Optional[dict] = None,
    ) -> Optional[PhotoAvatar]:
        avatar = await self.get_by_id(avatar_id)
        if not avatar:
            return None
        if head_glb_url is not None:
            avatar.head_glb_url = head_glb_url
        if body_glb_url is not None:
            avatar.body_glb_url = body_glb_url
        if merged_glb_url is not None:
            avatar.merged_glb_url = merged_glb_url
        if neck_joint is not None:
            avatar.neck_joint = neck_joint
        await self.db.commit()
        await self.db.refresh(avatar)
        return avatar

    async def soft_delete(self, avatar_id: int) -> bool:
        avatar = await self.get_by_id(avatar_id)
        if not avatar:
            return False
        avatar.is_deleted = True
        await self.db.commit()
        return True
