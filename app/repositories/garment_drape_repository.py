from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.garment_drape import GarmentDrape


class GarmentDrapeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_cached(
        self, garment_id: int, beta_hash: str, size: str
    ) -> Optional[GarmentDrape]:
        result = await self.db.execute(
            select(GarmentDrape).where(
                GarmentDrape.garment_id == garment_id,
                GarmentDrape.beta_hash == beta_hash,
                GarmentDrape.size == size,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        garment_id: int,
        beta_hash: str,
        size: str,
        glb_url: str,
        heatmap_glb_url: Optional[str] = None,
    ) -> GarmentDrape:
        drape = GarmentDrape(
            garment_id=garment_id,
            beta_hash=beta_hash,
            size=size,
            glb_url=glb_url,
            heatmap_glb_url=heatmap_glb_url,
        )
        self.db.add(drape)
        await self.db.commit()
        await self.db.refresh(drape)
        return drape
