from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from models.product_embedding import ProductEmbedding, EMBED_DIM


class EmbeddingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert(self, data: dict) -> None:
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
            {"vec": str(vector), "k": top_k, "threshold": 0.72},
        )
        return [dict(r._mapping) for r in result]

    async def get_all(self, skip: int, limit: int, search: str = "") -> list[dict]:
        where = "WHERE (name ILIKE :search OR brand ILIKE :search)" if search else ""
        result = await self.db.execute(
            text(f"""
                SELECT firestore_product_id, name, brand, price, images_json,
                    text_embedding IS NOT NULL as has_text,
                    image_embedding IS NOT NULL as has_image,
                    updated_at
                FROM product_embeddings
                {where}
                ORDER BY updated_at DESC
                LIMIT :limit OFFSET :skip
            """),
            {"search": f"%{search}%", "limit": limit, "skip": skip} if search
            else {"limit": limit, "skip": skip}
        )
        return [dict(r._mapping) for r in result]

    async def count(self, search: str = "") -> int:
        where = "WHERE (name ILIKE :search OR brand ILIKE :search)" if search else ""
        result = await self.db.execute(
            text(f"SELECT COUNT(*) FROM product_embeddings {where}"),
            {"search": f"%{search}%"} if search else {}
        )
        return result.scalar()

    async def get_stats(self) -> dict:
        result = await self.db.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(text_embedding) as has_text,
                COUNT(image_embedding) as has_image,
                COUNT(*) FILTER (
                    WHERE text_embedding IS NOT NULL
                    AND image_embedding IS NOT NULL
                ) as has_both
            FROM product_embeddings
        """))
        return dict(result.mappings().one())

    async def delete(self, firestore_product_id: str) -> None:
        await self.db.execute(
            text("DELETE FROM product_embeddings WHERE firestore_product_id = :pid"),
            {"pid": firestore_product_id}
        )
        await self.db.commit()