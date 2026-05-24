"""
routers/fit_router.py
---------------------
Chức năng gợi ý size — tách hoàn toàn khỏi ghép ảnh.

Endpoints:
    POST /fit/suggest          → gợi ý size (user đã lưu profile hoặc nhập tay)
    GET  /fit/size-chart       → trả bảng size chart cơ bản để FE hiển thị
    GET  /fit/garment/{id}/sizes → trả size specs của garment cụ thể
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from repositories.body_profile_repository import BodyProfileRepository
from repositories.garment_size_spec_repository import GarmentSizeSpecRepository
from services.fit_assessment_service import FitAssessmentService

router = APIRouter(prefix="/fit", tags=["fit"])


# ══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class GuestMeasurements(BaseModel):
    """
    Số đo nhập tay — hỗ trợ cả 2 mode:
        Basic:  height_cm + weight_kg
        Detail: chest_cm / waist_cm / hip_cm (có thể kết hợp với height/weight)
    """
    height_cm: Optional[float] = Field(None, gt=100, lt=230, description="Chiều cao (cm)")
    weight_kg: Optional[float] = Field(None, gt=20,  lt=200, description="Cân nặng (kg)")
    chest_cm:  Optional[float] = Field(None, gt=50,  lt=200, description="Vòng ngực (cm)")
    waist_cm:  Optional[float] = Field(None, gt=40,  lt=180, description="Vòng eo (cm)")
    hip_cm:    Optional[float] = Field(None, gt=50,  lt=200, description="Vòng hông (cm)")
    gender:    str              = Field("neutral", description="male | female | neutral")

    @model_validator(mode="after")
    def check_minimum_data(self):
        has_basic  = self.height_cm and self.weight_kg
        has_detail = sum(
            1 for v in [self.chest_cm, self.waist_cm, self.hip_cm] if v
        ) >= 1
        if not has_basic and not has_detail:
            raise ValueError(
                "Cần ít nhất height_cm + weight_kg, hoặc một trong chest/waist/hip."
            )
        return self


class SuggestRequest(BaseModel):
    """
    Request body cho POST /fit/suggest.
    Bắt buộc có garment_id.
    Một trong hai: user_id (lấy profile từ DB) hoặc measurements (nhập tay).
    """
    garment_id:    int                         = Field(..., gt=0)
    user_id:       Optional[int]               = Field(None, gt=0)
    measurements:  Optional[GuestMeasurements] = None
    selected_size: Optional[str]               = Field(None, description="Size muốn kiểm tra cụ thể, VD: 'M'")

    @model_validator(mode="after")
    def check_source(self):
        if self.user_id is None and self.measurements is None:
            raise ValueError("Cần cung cấp user_id hoặc measurements.")
        return self


class SizeSpecIn(BaseModel):
    """
    Schema để shop nhập size spec cho garment.

    Bắt buộc:
        - size_label
        - weight_min_kg + weight_max_kg  ← để gợi ý size theo cân nặng
    Khuyến nghị nhập thêm:
        - height_min_cm + height_max_cm  ← gợi ý chính xác hơn
        - chest_cm / waist_cm / hip_cm   ← để tính ease (DETAIL mode)
    """
    size_label:     str   = Field(..., description="XS | S | M | L | XL | XXL | XXXL")

    # Bắt buộc — BASIC mode
    weight_min_kg:  float = Field(..., gt=0, lt=200, description="Cân nặng tối thiểu khuyến nghị (kg)")
    weight_max_kg:  float = Field(..., gt=0, lt=200, description="Cân nặng tối đa khuyến nghị (kg)")

    # Khuyến nghị — BASIC mode chính xác hơn
    height_min_cm:  Optional[float] = Field(None, gt=100, lt=230, description="Chiều cao tối thiểu khuyến nghị (cm)")
    height_max_cm:  Optional[float] = Field(None, gt=100, lt=230, description="Chiều cao tối đa khuyến nghị (cm)")

    # Tuỳ chọn — DETAIL mode
    chest_cm:       Optional[float] = Field(None, gt=0, description="Vòng ngực quần áo (cm)")
    waist_cm:       Optional[float] = Field(None, gt=0, description="Vòng eo quần áo (cm)")
    hip_cm:         Optional[float] = Field(None, gt=0, description="Vòng hông quần áo (cm)")
    shoulder_cm:    Optional[float] = Field(None, gt=0, description="Rộng vai (cm)")
    length_cm:      Optional[float] = Field(None, gt=0, description="Chiều dài sản phẩm (cm)")
    sleeve_cm:      Optional[float] = Field(None, gt=0, description="Dài tay (cm)")
    inseam_cm:      Optional[float] = Field(None, gt=0, description="Dài đũng (cm)")

    @model_validator(mode="after")
    def check_weight_range(self):
        if self.weight_min_kg >= self.weight_max_kg:
            raise ValueError("weight_min_kg phải nhỏ hơn weight_max_kg")
        if self.height_min_cm is not None and self.height_max_cm is not None:
            if self.height_min_cm >= self.height_max_cm:
                raise ValueError("height_min_cm phải nhỏ hơn height_max_cm")
        # Nếu nhập 1 trong 2 height thì phải nhập cả 2
        if (self.height_min_cm is None) != (self.height_max_cm is None):
            raise ValueError("Phải nhập cả height_min_cm lẫn height_max_cm, không được nhập thiếu một.")
        return self


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/suggest")
async def suggest_size(
    body: SuggestRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Gợi ý size quần áo.

    **Trường hợp 1 — User đã lưu body profile:**
    ```json
    { "garment_id": 1, "user_id": 42 }
    ```

    **Trường hợp 2 — Nhập tay cơ bản (height + weight):**
    ```json
    {
        "garment_id": 1,
        "measurements": { "height_cm": 165, "weight_kg": 55, "gender": "female" }
    }
    ```

    **Trường hợp 3 — Nhập tay chi tiết (số đo vòng ngực/eo/hông):**
    ```json
    {
        "garment_id": 1,
        "measurements": {
            "chest_cm": 86, "waist_cm": 68, "hip_cm": 92,
            "height_cm": 165, "weight_kg": 55, "gender": "female"
        },
        "selected_size": "M"
    }
    ```
    """
    body_repo      = BodyProfileRepository(db)
    size_spec_repo = GarmentSizeSpecRepository(db)
    service        = FitAssessmentService(body_repo, size_spec_repo)

    guest = body.measurements.model_dump() if body.measurements else None

    return await service.suggest(
        garment_id=body.garment_id,
        user_id=body.user_id,
        guest_measurements=guest,
        selected_size=body.selected_size,
    )


@router.get("/garment/{garment_id}/sizes")
async def get_garment_sizes(
    garment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Trả danh sách size specs của một garment cụ thể."""
    repo  = GarmentSizeSpecRepository(db)
    specs = await repo.get_by_garment_id(garment_id)
    if not specs:
        return {"garment_id": garment_id, "sizes": [], "has_size_chart": False}
    return {
        "garment_id":    garment_id,
        "has_size_chart": True,
        "sizes": [s.to_dict() for s in specs],
    }


@router.put("/garment/{garment_id}/sizes")
async def upsert_garment_sizes(
    garment_id: int,
    sizes: list[SizeSpecIn],
    db: AsyncSession = Depends(get_db),
):
    """
    Admin endpoint: nhập/cập nhật bảng size cho garment.
    Gửi toàn bộ danh sách size cùng lúc.
    """
    repo = GarmentSizeSpecRepository(db)
    saved = await repo.bulk_upsert(
        garment_id,
        [s.model_dump() for s in sizes],
    )
    return {
        "garment_id": garment_id,
        "updated":    len(saved),
        "sizes":      [s.to_dict() for s in saved],
    }