from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base


class Garment(Base):
    __tablename__ = "garments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    model_url: Mapped[str] = mapped_column(String(1000), nullable=False)   # Cloudinary URL .glb
    public_id: Mapped[str] = mapped_column(String(500), nullable=False)    # Cloudinary public_id
    local_url:Mapped[str]=mapped_column(String(1000), nullable=True)    # Local URL for testing
    item_index: Mapped[int] = mapped_column(Integer, nullable=True)        # vị trí trong Carousel demo
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )