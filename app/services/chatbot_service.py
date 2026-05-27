import json
import asyncio
import ollama
from repositories.chat_repository import ChatRepository
from repositories.embedding_repository import EmbeddingRepository
from services.embedding_service import embed_text
from schemas.chatbot import ProductOut

MODEL = "qwen2.5:7b"

SYSTEM_PROMPT = """Bạn là GlowUp Helper, trợ lý tư vấn thời trang và làm đẹp của GlowUp Store.

Nhiệm vụ:
- Tư vấn sản phẩm phù hợp dựa trên nhu cầu khách hàng
- Giải thích lý do gợi ý ngắn gọn, thân thiện
- Trả lời bằng tiếng Việt, ngắn gọn (tối đa 3-4 câu)
- Nếu có sản phẩm phù hợp, đề cập tên sản phẩm cụ thể
- Không bịa thông tin không có trong danh sách sản phẩm

Nếu không có sản phẩm phù hợp, hãy nói thật và hỏi thêm nhu cầu của khách.
QUAN TRỌNG: Bạn PHẢI trả lời hoàn toàn bằng tiếng Việt. Tuyệt đối không dùng tiếng Anh, tiếng Trung."""

EXCLUDE_MAP = {
    "áo": ["quần", "short", "jean", "kaki", "baggy", "legging"],
    "quần": ["áo", "polo", "len", "sơ mi", "khoác", "blazer", "blouse"],
    "túi": ["quần", "áo", "short", "jean"],
    "váy": ["quần", "áo", "túi", "short"],
    "giày": ["quần", "áo", "túi", "váy"],
}

def _keyword_filter(rows: list[dict], query: str) -> list[dict]:
    query_lower = query.lower()
    exclude_words: list[str] = []
    for category, excludes in EXCLUDE_MAP.items():
        if category in query_lower:
            exclude_words = excludes
            break
    if not exclude_words:
        return rows
    return [
        r for r in rows
        if not any(w in (r.get("name") or "").lower() for w in exclude_words)
    ]


def _build_query_text(message: str) -> str:
    msg = message.lower()
    prefix_parts = []
    if any(w in msg for w in ["áo", "shirt", "blouse", "polo", "len", "sơ mi", "khoác", "blazer"]):
        prefix_parts.append("[áo]")
    elif any(w in msg for w in ["quần", "short", "jean", "kaki", "baggy", "legging"]):
        prefix_parts.append("[quần]")
    elif any(w in msg for w in ["túi", "bag", "tote", "xách", "đeo"]):
        prefix_parts.append("[túi]")
    elif any(w in msg for w in ["váy", "skirt", "dress"]):
        prefix_parts.append("[váy]")
    elif any(w in msg for w in ["giày", "dép", "sandal", "boot"]):
        prefix_parts.append("[giày]")
    if any(w in msg for w in ["nữ", "female", "cô", "girl"]):
        prefix_parts.append("[Female]")
    elif any(w in msg for w in ["nam", "male", "anh", "boy"]):
        prefix_parts.append("[Male]")
    return f"{' '.join(prefix_parts)} {message}".strip()


def warmup_model():
    try:
        ollama.chat(model=MODEL, messages=[{"role": "user", "content": "hi"}], options={"num_predict": 1})
        print(f"[chatbot] ✓ Model {MODEL} warm up xong")
    except Exception as e:
        print(f"[chatbot] ✗ Warm up lỗi: {e}")


def _format_context(products: list[dict]) -> str:
    if not products:
        return "Không tìm thấy sản phẩm phù hợp."
    lines = []
    for p in products:
        price = f"{p.get('price', 0):,}đ".replace(",", ".")
        lines.append(f"- {p.get('name', '')} | {p.get('brand', '')} | {price}")
    return "\n".join(lines)


def _to_product_out(row: dict) -> ProductOut:
    return ProductOut(
        id=row["firestore_product_id"],
        name=row.get("name", ""),
        price=row.get("price", 0),
        images=row.get("images_json") or "[]",
        brand=row.get("brand", ""),
        score=round(float(row.get("score", 0)), 4),
    )


def _call_ollama(msgs: list[dict]) -> str:
    response = ollama.chat(
        model=MODEL,
        messages=msgs,
        options={"temperature": 0.7, "num_predict": 512},
    )
    return response["message"]["content"]


class ChatbotService:
    def __init__(self, chat_repo: ChatRepository, embed_repo: EmbeddingRepository):
        self.chat_repo  = chat_repo
        self.embed_repo = embed_repo

    async def create_session(self, user_id: int, title: str):
        return await self.chat_repo.create_session(user_id, title)

    async def get_session(self, session_id: int):
        return await self.chat_repo.get_session(session_id)

    async def get_sessions(self, user_id: int, skip: int, limit: int):
        return await self.chat_repo.get_sessions_by_user(user_id, skip, limit)

    async def update_session_title(self, session_id: int, title: str):
        return await self.chat_repo.update_session_title(session_id, title)

    async def delete_session(self, session_id: int):
        await self.chat_repo.delete_session(session_id)

    async def delete_message(self, message_id: int):
        await self.chat_repo.delete_message(message_id)

    async def chat(self, session_id: int, user_id: int, message: str) -> dict:
        try:
            query_text = _build_query_text(message)
            print(f"[chat] query_text: {query_text}")

            history, query_vec = await asyncio.gather(
                self.chat_repo.get_messages(session_id),
                asyncio.get_event_loop().run_in_executor(None, embed_text, query_text),
            )

            rows = await self.embed_repo.search_by_text(query_vec, top_k=3)
            rows = _keyword_filter(rows, message)
            rows = rows[:2]

            context = _format_context(rows)
            msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
            for h in history[-6:]:
                msgs.append({"role": h.role, "content": h.content})
            msgs.append({
                "role": "user",
                "content": f"{message}\n\n[Sản phẩm có sẵn:]\n{context}",
            })

            reply = await asyncio.get_event_loop().run_in_executor(None, _call_ollama, msgs)

            products     = [_to_product_out(r) for r in rows]
            products_str = json.dumps([p.model_dump() for p in products], ensure_ascii=False)

            await self.chat_repo.add_message(session_id, "user", message)
            await self.chat_repo.add_message(session_id, "assistant", reply, suggested_products=products_str)

            if len(history) == 0:
                short_title = message[:60] + ("..." if len(message) > 60 else "")
                await self.chat_repo.update_session_title(session_id, short_title)

            return {
                "message":            reply,
                "suggested_products": products,
                "session_id":         session_id,
            }

        except Exception as e:
            import traceback
            print(f"[chat] LỖI: {e}")
            traceback.print_exc()
            raise

    async def get_embeddings(self, skip: int, limit: int, search: str = "") -> dict:
        items = await self.embed_repo.get_all(skip, limit, search)
        total = await self.embed_repo.count(search)
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    async def get_embedding_stats(self) -> dict:
        return await self.embed_repo.get_stats()

    async def delete_embedding(self, firestore_product_id: str) -> None:
        await self.embed_repo.delete(firestore_product_id)