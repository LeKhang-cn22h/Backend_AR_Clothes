"""
embedding_service.py
- Đọc sản phẩm từ Firebase
- Embed bằng nomic-embed-text (text only)
- Lưu vào Neon qua pgvector
"""
import json
import ollama
import firebase_admin
import os
from firebase_admin import credentials, firestore as fs
from repositories.embedding_repository import EmbeddingRepository

TEXT_MODEL = "nomic-embed-text"


def _get_firestore():
    if not firebase_admin._apps:
        base = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base, "serviceAccountKey.json"),
            os.path.join(base, "..", "serviceAccountKey.json"),
        ]
        key_path = next((p for p in candidates if os.path.exists(p)), None)
        if not key_path:
            raise FileNotFoundError("Không tìm thấy serviceAccountKey.json")
        firebase_admin.initialize_app(credentials.Certificate(os.path.abspath(key_path)))
    return fs.client()


def embed_text(text: str) -> list[float]:
    resp = ollama.embed(model=TEXT_MODEL, input=text)
    return resp["embeddings"][0]


def build_text_input(data: dict) -> str:
    name       = data.get("name", "")
    brand      = data.get("brand", "")
    desc       = data.get("description", "")
    category   = data.get("category", "")
    gender     = data.get("gender", "")
    short_desc = desc[:100] if desc else ""

    parts = []
    if category:   parts.append(f"[{category}]")
    if gender:     parts.append(f"[{gender}]")
    parts.append(name)
    if brand:      parts.append(brand)
    if short_desc: parts.append(short_desc)

    return " | ".join(parts)


async def sync_all_products(repo: EmbeddingRepository) -> dict:
    db_fs = _get_firestore()
    docs  = db_fs.collection("products").stream()

    success = 0
    failed  = 0

    for doc in docs:
        try:
            data   = doc.to_dict()
            name   = data.get("name", "")
            brand  = data.get("brand", "")
            price  = data.get("price", 0)
            images = data.get("images", [])

            text_input = build_text_input(data)
            text_vec   = embed_text(text_input)
            print(f"[sync] text_input: {text_input[:80]}")

            await repo.upsert({
                "firestore_product_id": doc.id,
                "name":           name,
                "brand":          brand,
                "price":          price,
                "images_json":    json.dumps(images),
                "text_embedding": text_vec,
                "image_embedding": None,
            })
            success += 1
            print(f"[sync] ✓ {name[:50]}")

        except Exception as e:
            failed += 1
            print(f"[sync] ✗ {doc.id}: {e}")

    return {"success": success, "failed": failed}