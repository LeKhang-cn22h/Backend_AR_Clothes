from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models.ar_session import ARSession
from schemas.ar_session import ARSessionCreate


class ARSessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: ARSessionCreate) -> ARSession:
        session = ARSession(**data.model_dump())
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_by_id(self, id: int) -> Optional[ARSession]:
        result = await self.db.execute(select(ARSession).where(ARSession.id == id))
        return result.scalar_one_or_none()

    async def get_all(
        self,
        user_id: Optional[int] = None,
        garment_id: Optional[int] = None,
        converted: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ARSession]:
        query = select(ARSession)
        if user_id is not None:
            query = query.where(ARSession.user_id == user_id)
        if garment_id is not None:
            query = query.where(ARSession.garment_id == garment_id)
        if converted is not None:
            query = query.where(ARSession.converted == converted)
        query = query.offset(skip).limit(limit).order_by(ARSession.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(self, id: int, **kwargs) -> Optional[ARSession]:
        session = await self.get_by_id(id)
        if not session:
            return None
        for field, value in kwargs.items():
            setattr(session, field, value)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def delete(self, id: int) -> bool:
        session = await self.get_by_id(id)
        if not session:
            return False
        await self.db.delete(session)
        await self.db.commit()
        return True

    async def count(self, converted: Optional[bool] = None) -> int:
        query = select(func.count()).select_from(ARSession)
        if converted is not None:
            query = query.where(ARSession.converted == converted)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_top_garments(self, limit: int = 5) -> list[dict]:
        query = (
            select(ARSession.garment_id, func.count(ARSession.id).label("session_count"))
            .group_by(ARSession.garment_id)
            .order_by(func.count(ARSession.id).desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return [{"garment_id": row.garment_id, "session_count": row.session_count} for row in result.all()]
