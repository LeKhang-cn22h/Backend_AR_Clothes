import enum
from datetime import datetime
from sqlalchemy import Boolean, Integer, String, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base


class ConversionEventType(str, enum.Enum):
    view = "view"
    ar_try_on = "ar_try_on"
    add_to_cart = "add_to_cart"
    purchase = "purchase"


class ConversionEvent(Base):
    __tablename__ = "conversion_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    firestore_product_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    garment_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("garments.id"), nullable=True)
    event_type: Mapped[ConversionEventType] = mapped_column(Enum(ConversionEventType), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="conversion_events")
    garment = relationship("Garment", back_populates="conversion_events")
