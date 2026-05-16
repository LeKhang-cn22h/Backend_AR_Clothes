from datetime import datetime
from sqlalchemy import Integer, String, DateTime, func, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from core.database import Base

EMBED_DIM = 768  # nomic-embed-text / nomic-embed-vision output dim


class ProductEmbedding(Base):
    __tablename__ = "product_embeddings"

    id:                  Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    firestore_product_id: Mapped[str]     = mapped_column(String(100), nullable=False, unique=True, index=True)
    name:                Mapped[str]      = mapped_column(String(500), nullable=False)
    brand:               Mapped[str]      = mapped_column(String(100), nullable=True)
    price:               Mapped[int]      = mapped_column(Integer, nullable=True)
    images_json:         Mapped[str]      = mapped_column(String(2000), nullable=True)   # JSON string
    text_embedding:      Mapped[list[float]] = mapped_column(Vector(EMBED_DIM), nullable=True)
    image_embedding:     Mapped[list[float]] = mapped_column(Vector(EMBED_DIM), nullable=True)
    synced_at:           Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index(
            "ix_product_text_embedding_hnsw",
            "text_embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"text_embedding": "vector_cosine_ops"},
        ),
        Index(
            "ix_product_image_embedding_hnsw",
            "image_embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"image_embedding": "vector_cosine_ops"},
        ),
    )