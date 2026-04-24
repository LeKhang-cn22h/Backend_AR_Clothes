from datetime import datetime
from sqlalchemy import Boolean, Integer, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base


class GarmentCategory(Base):
    __tablename__ = "garment_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    garments = relationship("Garment", back_populates="category")
