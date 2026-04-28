from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class GarmentDrape(Base):
    __tablename__ = "garment_drapes"
    __table_args__ = (
        UniqueConstraint(
            "garment_id",
            "beta_hash",
            "size",
            name="uq_garment_drapes_garment_beta_size",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    garment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("garments.id"), nullable=False, index=True
    )
    beta_hash: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    size: Mapped[str] = mapped_column(String(10), nullable=False)
    glb_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    heatmap_glb_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    garment = relationship("Garment", back_populates="garment_drapes")
