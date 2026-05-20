from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

class PhotoTryonSession(Base):
    __tablename__ = "photo_tryon_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    garment_id: Mapped[int] = mapped_column(Integer, ForeignKey("garments.id"), nullable=False, index=True)
    person_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    result_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    result_public_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cloth_type: Mapped[str] = mapped_column(String(20), default="upper", nullable=False)
    selected_size: Mapped[str | None] = mapped_column(String(10), nullable=True)
    suggested_size: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fit_warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="photo_tryon_sessions")
    garment = relationship("Garment", back_populates="photo_tryon_sessions")
