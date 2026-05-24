"""
models/garment_size_spec.py
---------------------------
Lưu bảng size chart của từng garment theo từng size label.
Mỗi record gồm 2 nhóm thông tin:

    1. Số đo quần áo (garment measurements) — dùng cho DETAIL mode:
       chest_cm, waist_cm, hip_cm, shoulder_cm, length_cm, sleeve_cm, inseam_cm
       → tính ease = garment_cm - body_cm để đánh giá độ vừa

    2. Khuyến nghị cơ thể của shop — dùng cho BASIC mode:
       height_min_cm, height_max_cm, weight_min_kg, weight_max_kg
       → tra theo chiều cao + cân nặng user để gợi ý size
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class GarmentSizeSpec(Base):
    __tablename__ = "garment_size_specs"

    # Một garment không được có 2 record cùng size_label
    __table_args__ = (
        UniqueConstraint("garment_id", "size_label", name="uq_garment_size"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    garment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("garments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Size label ───────────────────────────────────────────────────────────
    size_label: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="XS | S | M | L | XL | XXL | XXXL",
    )

    # ── Số đo quần áo (cm) ──────────────────────────────────────────────────
    chest_cm: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 1), nullable=True, comment="Vòng ngực quần áo (cm)"
    )
    waist_cm: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 1), nullable=True, comment="Vòng eo quần áo (cm)"
    )
    hip_cm: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 1), nullable=True, comment="Vòng hông quần áo (cm)"
    )
    shoulder_cm: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 1), nullable=True, comment="Rộng vai (cm)"
    )
    length_cm: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 1), nullable=True, comment="Chiều dài sản phẩm (cm)"
    )
    sleeve_cm: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 1), nullable=True, comment="Dài tay (cm) — áo"
    )
    inseam_cm: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 1), nullable=True, comment="Dài đũng (cm) — quần"
    )

    # ── Khuyến nghị cơ thể của shop (BASIC mode) ────────────────────────────
    height_min_cm: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 1), nullable=True, comment="Chiều cao tối thiểu khuyến nghị (cm)"
    )
    height_max_cm: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 1), nullable=True, comment="Chiều cao tối đa khuyến nghị (cm)"
    )
    weight_min_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 1), nullable=True, comment="Cân nặng tối thiểu khuyến nghị (kg)"
    )
    weight_max_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 1), nullable=True, comment="Cân nặng tối đa khuyến nghị (kg)"
    )

    # ── Metadata ─────────────────────────────────────────────────────────────
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    garment = relationship("Garment", back_populates="size_specs")

    # ── Helper ────────────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        """Chuyển sang dict để dùng trong fit_assessment_service."""
        return {
            # Size label
            "size_label":     self.size_label,
            # Số đo quần áo — DETAIL mode
            "chest_cm":       float(self.chest_cm)       if self.chest_cm       else None,
            "waist_cm":       float(self.waist_cm)       if self.waist_cm       else None,
            "hip_cm":         float(self.hip_cm)         if self.hip_cm         else None,
            "shoulder_cm":    float(self.shoulder_cm)    if self.shoulder_cm    else None,
            "length_cm":      float(self.length_cm)      if self.length_cm      else None,
            "sleeve_cm":      float(self.sleeve_cm)      if self.sleeve_cm      else None,
            "inseam_cm":      float(self.inseam_cm)      if self.inseam_cm      else None,
            # Khuyến nghị cơ thể — BASIC mode
            "height_min_cm":  float(self.height_min_cm)  if self.height_min_cm  else None,
            "height_max_cm":  float(self.height_max_cm)  if self.height_max_cm  else None,
            "weight_min_kg":  float(self.weight_min_kg)  if self.weight_min_kg  else None,
            "weight_max_kg":  float(self.weight_max_kg)  if self.weight_max_kg  else None,
        }