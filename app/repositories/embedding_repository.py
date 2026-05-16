from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from models.product_embedding import ProductEmbedding, EMBED_DIM


class EmbeddingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert(self, data: dict) -> None:
        """Thêm hoặc cập nhật embedding cho 1 sản phẩm."""
        existing = await self.db.execute(
            select(ProductEmbedding).where(
                ProductEmbedding.firestore_product_id == data["firestore_product_id"]
            )
        )
        obj = existing.scalar_one_or_none()
        if obj:
            for k, v in data.items():
                setattr(obj, k, v)
        else:
            obj = ProductEmbedding(**data)
            self.db.add(obj)
        await self.db.commit()

    async def search_by_text(self, vector: list[float], top_k: int = 5) -> list[dict]:
        result = await self.db.execute(
            text("""
                SELECT firestore_product_id, name, brand, price, images_json,
                    1 - (text_embedding <=> CAST(:vec AS vector)) AS score
                FROM product_embeddings
                WHERE text_embedding IS NOT NULL
                AND 1 - (text_embedding <=> CAST(:vec AS vector)) > :threshold
                ORDER BY text_embedding <=> CAST(:vec AS vector)
                LIMIT :k
            """),
            {"vec": str(vector), "k": 2, "threshold": 0.72},
        )
        return [dict(r._mapping) for r in result]

    async def search_by_image(self, vector: list[float], top_k: int = 5) -> list[dict]:
        result = await self.db.execute(
            text("""
                SELECT firestore_product_id, name, brand, price, images_json,
                    1 - (image_embedding <=> CAST(:vec AS vector)) AS score
                FROM product_embeddings
                WHERE image_embedding IS NOT NULL
                AND 1 - (image_embedding <=> CAST(:vec AS vector)) > :threshold
                ORDER BY image_embedding <=> CAST(:vec AS vector)
                LIMIT :k
            """),
            {"vec": str(vector), "k": top_k, "threshold": 0.6},
        )
        return [dict(r._mapping) for r in result]

    async def count(self) -> int:
        result = await self.db.execute(text("SELECT COUNT(*) FROM product_embeddings"))
        return result.scalar()