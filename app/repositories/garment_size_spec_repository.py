from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.garment_size_spec import GarmentSizeSpec


class GarmentSizeSpecRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_garment_id(self, garment_id: int) -> list[GarmentSizeSpec]:
        result = await self.db.execute(
            select(GarmentSizeSpec).where(
                GarmentSizeSpec.garment_id == garment_id,
                GarmentSizeSpec.is_deleted == False,
            )
        )
        return list(result.scalars().all())

    async def get_by_garment_and_size(
        self, garment_id: int, size_label: str
    ) -> Optional[GarmentSizeSpec]:
        result = await self.db.execute(
            select(GarmentSizeSpec).where(
                GarmentSizeSpec.garment_id == garment_id,
                GarmentSizeSpec.size_label == size_label.upper(),
                GarmentSizeSpec.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(self, garment_id: int, size_label: str, data: dict) -> GarmentSizeSpec:
        """Tạo mới hoặc cập nhật nếu đã tồn tại."""
        if data.get("weight_min_kg") is None or data.get("weight_max_kg") is None:
            raise ValueError(
                f"size_label='{size_label}': weight_min_kg và weight_max_kg là bắt buộc."
            )
        existing = await self.get_by_garment_and_size(garment_id, size_label)
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        spec = GarmentSizeSpec(
            garment_id=garment_id,
            size_label=size_label.upper(),
            **data,
        )
        self.db.add(spec)
        await self.db.commit()
        await self.db.refresh(spec)
        return spec

    async def bulk_upsert(
        self, garment_id: int, sizes: list[dict]
    ) -> list[GarmentSizeSpec]:
        """
        Nhận list dict [{size_label, chest_cm, waist_cm, ...}],
        upsert tất cả cùng lúc.
        """
        results = []
        for item in sizes:
            size_label = item.pop("size_label", None)
            if not size_label:
                continue
            spec = await self.upsert(garment_id, size_label, item)
            results.append(spec)
        return results

    async def soft_delete_by_garment(self, garment_id: int) -> int:
        """Soft delete toàn bộ size specs của một garment. Trả về số bản ghi bị xoá."""
        specs = await self.get_by_garment_id(garment_id)
        for spec in specs:
            spec.is_deleted = True
        await self.db.commit()
        return len(specs)