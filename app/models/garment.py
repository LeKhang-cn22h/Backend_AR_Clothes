import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Garment(Base):
    __tablename__ = "garments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    model_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    public_id: Mapped[str] = mapped_column(String(500), nullable=False)
    item_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("garment_categories.id"), nullable=True
    )
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category = relationship("GarmentCategory", back_populates="garments")
    store = relationship("Store", back_populates="garments")
    ar_sessions = relationship("ARSession", back_populates="garment")
    wishlists = relationship("Wishlist", back_populates="garment")
    conversion_events = relationship("ConversionEvent", back_populates="garment")
