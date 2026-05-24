"""
Lưu lịch sử mỗi lần user ghép ảnh thử đồ.

Thiết kế:
- user_id nullable  → guest (chưa đăng nhập) vẫn có thể thử đồ
- garment_id nullable → trường hợp upload cloth thủ công (không từ catalog)
- Không lưu kết quả gợi ý size vì tính toán nhanh, luôn reproducible
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class TryonHistory(Base):
    __tablename__ = "tryon_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Liên kết ─────────────────────────────────────────────────────────────
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="NULL nếu guest chưa đăng nhập",
    )
    garment_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("garments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="NULL nếu user upload cloth thủ công",
    )

    # ── Kết quả ảnh ──────────────────────────────────────────────────────────
    result_image_url: Mapped[str] = mapped_column(
        String, nullable=False, comment="URL ảnh kết quả trên Cloudinary"
    )
    public_id: Mapped[str | None] = mapped_column(
        String, nullable=True, comment="Cloudinary public_id — dùng để xoá sau"
    )
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Tham số inference ────────────────────────────────────────────────────
    cloth_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="upper",
        comment="upper | lower | overall",
    )
    seed: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Seed dùng để reproduce kết quả"
    )
    num_steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    guidance: Mapped[float | None] = mapped_column(
        # dùng Float thay Numeric cho tiện
        nullable=True,
        comment="Guidance scale của diffusion model",
    )
    resolution: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="768x1024 | 1152x1536 | 1536x2048"
    )

    # ── Metadata ─────────────────────────────────────────────────────────────
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user    = relationship("User",    back_populates="tryon_history")
    garment = relationship("Garment", back_populates="tryon_history")