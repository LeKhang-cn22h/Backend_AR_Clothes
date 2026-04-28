from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class PhotoTryonSession(Base):
    __tablename__ = "photo_tryon_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    avatar_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("photo_avatars.id"), nullable=False, index=True
    )
    garment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("garments.id"), nullable=False, index=True
    )
    selected_size: Mapped[str] = mapped_column(String(10), nullable=False)
    suggested_size: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fit_warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="photo_tryon_sessions")
    avatar = relationship("PhotoAvatar", back_populates="photo_tryon_sessions")
    garment = relationship("Garment", back_populates="photo_tryon_sessions")
