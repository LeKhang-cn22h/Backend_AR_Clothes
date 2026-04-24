from typing import Optional
from fastapi import HTTPException
from models.ar_session import ARSession
from repositories.ar_session_repository import ARSessionRepository
from repositories.garment_repository import GarmentRepository
from schemas.ar_session import ARSessionCreate


class ARSessionService:
    def __init__(self, repo: ARSessionRepository, garment_repo: GarmentRepository):
        self.repo = repo
        self.garment_repo = garment_repo

    async def create(self, data: ARSessionCreate) -> ARSession:
        garment = await self.garment_repo.get_by_id(data.garment_id)
        if not garment:
            raise HTTPException(status_code=404, detail="Khong tim thay garment")
        return await self.repo.create(data)

    async def get_by_id(self, id: int) -> ARSession:
        session = await self.repo.get_by_id(id)
        if not session:
            raise HTTPException(status_code=404, detail="Khong tim thay phien AR")
        return session

    async def get_all(
        self,
        user_id: Optional[int] = None,
        garment_id: Optional[int] = None,
        converted: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ARSession]:
        return await self.repo.get_all(
            user_id=user_id, garment_id=garment_id, converted=converted, skip=skip, limit=limit
        )

    async def mark_converted(self, id: int) -> ARSession:
        session = await self.repo.update(id, converted=True)
        if not session:
            raise HTTPException(status_code=404, detail="Khong tim thay phien AR")
        return session

    async def delete(self, id: int) -> None:
        deleted = await self.repo.delete(id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Khong tim thay phien AR")

    async def get_stats(self) -> dict:
        total = await self.repo.count()
        total_converted = await self.repo.count(converted=True)
        conversion_rate = round(total_converted / total * 100, 2) if total > 0 else 0.0
        top_garments = await self.repo.get_top_garments()
        return {
            "total_sessions": total,
            "total_converted": total_converted,
            "conversion_rate": conversion_rate,
            "top_garments": top_garments,
        }
