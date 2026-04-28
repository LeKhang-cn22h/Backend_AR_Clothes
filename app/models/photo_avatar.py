from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class PhotoAvatar(Base):
    __tablename__ = "photo_avatars"
    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'ready', 'failed')",
            name="photo_avatars_status_check",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    body_profile_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("body_profiles.id"), nullable=True, index=True
    )
    head_glb_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    body_glb_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    merged_glb_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    neck_joint: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="processing", nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="photo_avatars")
    body_profile = relationship("BodyProfile", back_populates="photo_avatars")
    photo_tryon_sessions = relationship(
        "PhotoTryonSession", back_populates="avatar"
    )
