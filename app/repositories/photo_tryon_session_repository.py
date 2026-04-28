from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.photo_tryon_session import PhotoTryonSession


class PhotoTryonSessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: Optional[int],
        avatar_id: int,
        garment_id: int,
        selected_size: str,
        suggested_size: Optional[str] = None,
        fit_warnings: Optional[list] = None,
    ) -> PhotoTryonSession:
        session = PhotoTryonSession(
            user_id=user_id,
            avatar_id=avatar_id,
            garment_id=garment_id,
            selected_size=selected_size,
            suggested_size=suggested_size,
            fit_warnings=fit_warnings,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_by_id(self, session_id: int) -> Optional[PhotoTryonSession]:
        result = await self.db.execute(
            select(PhotoTryonSession).where(
                PhotoTryonSession.id == session_id,
                PhotoTryonSession.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int) -> list[PhotoTryonSession]:
        result = await self.db.execute(
            select(PhotoTryonSession)
            .where(
                PhotoTryonSession.user_id == user_id,
                PhotoTryonSession.is_deleted == False,
            )
            .order_by(PhotoTryonSession.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_avatar_id(self, avatar_id: int) -> list[PhotoTryonSession]:
        result = await self.db.execute(
            select(PhotoTryonSession)
            .where(
                PhotoTryonSession.avatar_id == avatar_id,
                PhotoTryonSession.is_deleted == False,
            )
            .order_by(PhotoTryonSession.created_at.desc())
        )
        return list(result.scalars().all())
