from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class BodyProfile(Base):
    __tablename__ = "body_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    height: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    weight: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    chest: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    waist: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    hip: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    shoulder: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    arm_length: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    inseam: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    gender: Mapped[str] = mapped_column(String(10), default="neutral", nullable=False)
    beta_cache: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    beta_hash: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="body_profiles")
    photo_avatars = relationship("PhotoAvatar", back_populates="body_profile")
