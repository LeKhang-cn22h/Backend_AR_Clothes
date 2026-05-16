"""
embedding_service.py
- Đọc sản phẩm từ Firebase
- Embed bằng nomic-embed-text (text) và nomic-embed-vision (image)
- Lưu vào Neon qua pgvector
"""
import json
import base64
import httpx
import ollama
import firebase_admin
import os
from firebase_admin import credentials, firestore as fs
from repositories.embedding_repository import EmbeddingRepository


TEXT_MODEL  = "nomic-embed-text"
IMAGE_MODEL = "nomic-embed-vision"


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
    """
    Tạo text input cho embedding — ưu tiên name và category.
    Format: [category] name | brand | description ngắn
    """
    name     = data.get("name", "")
    brand    = data.get("brand", "")
    desc     = data.get("description", "")
    category = data.get("category", "")
    gender   = data.get("gender", "")

    # Lấy 100 ký tự đầu description để tránh noise
    short_desc = desc[:100] if desc else ""

    # Ưu tiên name + category + gender + brand
    parts = []
    if category: parts.append(f"[{category}]")
    if gender:   parts.append(f"[{gender}]")
    parts.append(name)
    if brand:    parts.append(brand)
    if short_desc: parts.append(short_desc)

    return " | ".join(parts)


def embed_image_from_url(image_url: str) -> list[float] | None:
    """Download ảnh → base64 → embed bằng nomic-embed-vision."""
    try:
        r = httpx.get(image_url, timeout=15)
        r.raise_for_status()
        b64 = base64.b64encode(r.content).decode()
        resp = ollama.embed(model=IMAGE_MODEL, input=b64)
        return resp["embeddings"][0]
    except Exception as e:
        print(f"[embed_image] lỗi {image_url}: {e}")
        return None


def embed_image_from_bytes(image_bytes: bytes) -> list[float]:
    """Embed ảnh từ bytes (dùng cho image search)."""
    b64 = base64.b64encode(image_bytes).decode()
    resp = ollama.embed(model=IMAGE_MODEL, input=b64)
    return resp["embeddings"][0]


async def sync_all_products(repo: EmbeddingRepository) -> dict:
    db_fs = _get_firestore()
    docs  = db_fs.collection("products").stream()

    success = 0
    failed  = 0

    for doc in docs:
        try:
            data     = doc.to_dict()
            pid      = doc.id
            name     = data.get("name", "")
            brand    = data.get("brand", "")
            price    = data.get("price", 0)
            images   = data.get("images", [])

            # Dùng build_text_input để embed đúng hơn
            text_input = build_text_input(data)
            text_vec   = embed_text(text_input)
            print(f"[sync] text_input: {text_input[:80]}")

            image_vec = None
            if images:
                image_vec = embed_image_from_url(images[0])

            await repo.upsert({
                "firestore_product_id": pid,
                "name":           name,
                "brand":          brand,
                "price":          price,
                "images_json":    json.dumps(images),
                "text_embedding": text_vec,
                "image_embedding": image_vec,
            })
            success += 1
            print(f"[sync] ✓ {name[:50]}")

        except Exception as e:
            failed += 1
            print(f"[sync] ✗ {doc.id}: {e}")

    return {"success": success, "failed": failed}