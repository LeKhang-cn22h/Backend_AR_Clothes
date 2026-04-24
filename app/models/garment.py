from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base


class Garment(Base):
    __tablename__ = "garments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    model_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    public_id: Mapped[str] = mapped_column(String(500), nullable=False)
    local_url: Mapped[str] = mapped_column(String(1000), nullable=True)
    item_index: Mapped[int] = mapped_column(Integer, nullable=True)
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("garment_categories.id"), nullable=True)
    firestore_product_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category = relationship("GarmentCategory", back_populates="garments")
    ar_sessions = relationship("ARSession", back_populates="garment")
    wishlists = relationship("Wishlist", back_populates="garment")
    conversion_events = relationship("ConversionEvent", back_populates="garment")
