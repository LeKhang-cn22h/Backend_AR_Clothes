from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.tryon_history import TryonHistory


class TryonHistoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> TryonHistory:
        record = TryonHistory(**data)
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def get_by_user_id(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[TryonHistory]:
        result = await self.db.execute(
            select(TryonHistory)
            .where(
                TryonHistory.user_id == user_id,
                TryonHistory.is_deleted == False,
            )
            .order_by(TryonHistory.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> Optional[TryonHistory]:
        result = await self.db.execute(
            select(TryonHistory).where(
                TryonHistory.id == record_id,
                TryonHistory.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> list[TryonHistory]:
        """Admin — lấy toàn bộ tryon history của tất cả users."""
        result = await self.db.execute(
            select(TryonHistory)
            .where(TryonHistory.is_deleted == False)
            .order_by(TryonHistory.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_all(self) -> int:
        """Admin — đếm tổng số records."""
        from sqlalchemy import func, select as sa_select
        result = await self.db.execute(
            sa_select(func.count()).select_from(TryonHistory)
            .where(TryonHistory.is_deleted == False)
        )
        return result.scalar() or 0

    async def soft_delete(self, record_id: int) -> bool:
        record = await self.get_by_id(record_id)
        if not record:
            return False
        record.is_deleted = True
        await self.db.commit()
        return True