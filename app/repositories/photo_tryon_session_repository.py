from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.photo_tryon_session import PhotoTryonSession


class PhotoTryonSessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> PhotoTryonSession:
        session = PhotoTryonSession(**data)
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

    async def list_by_user(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> list[PhotoTryonSession]:
        result = await self.db.execute(
            select(PhotoTryonSession)
            .where(
                PhotoTryonSession.user_id == user_id,
                PhotoTryonSession.is_deleted == False,
            )
            .order_by(PhotoTryonSession.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def soft_delete(self, session_id: int) -> Optional[PhotoTryonSession]:
        session = await self.get_by_id(session_id)
        if not session:
            return None
        session.is_deleted = True
        await self.db.commit()
        return session
