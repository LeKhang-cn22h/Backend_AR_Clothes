from fastapi import APIRouter, Depends, Query, UploadFile, File, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from repositories.chat_repository import ChatRepository
from repositories.embedding_repository import EmbeddingRepository
from services.chatbot_service import ChatbotService
from services.embedding_service import sync_all_products
from schemas.chatbot import (
    ChatRequest, ChatResponse, ChatResponseData,
    SessionCreate, SessionOut, SessionSummary,
    ImageSearchRequest, ImageSearchResponse,
)

router = APIRouter(prefix="/api/chatbot", tags=["Chatbot"])


def get_service(db: AsyncSession = Depends(get_db)) -> ChatbotService:
    return ChatbotService(ChatRepository(db), EmbeddingRepository(db))


# ── Sessions CRUD ────────────────────────────────────────────────

@router.post("/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionCreate, svc: ChatbotService = Depends(get_service)):
    return await svc.create_session(payload.user_id, payload.title)


@router.get("/sessions", response_model=list[SessionSummary])
async def get_sessions(
    user_id: int = Query(...),
    skip:    int = Query(default=0, ge=0),
    limit:   int = Query(default=20, ge=1, le=100),
    svc: ChatbotService = Depends(get_service),
):
    return await svc.get_sessions(user_id, skip, limit)


@router.get("/sessions/{session_id}", response_model=SessionOut)
async def get_session(session_id: int, svc: ChatbotService = Depends(get_service)):
    session = await svc.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session không tồn tại")
    return session


@router.patch("/sessions/{session_id}/title")
async def update_title(
    session_id: int,
    title: str = Query(..., min_length=1, max_length=255),
    svc: ChatbotService = Depends(get_service),
):
    session = await svc.update_session_title(session_id, title)
    if not session:
        raise HTTPException(status_code=404, detail="Session không tồn tại")
    return {"success": True, "title": session.title}


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: int, svc: ChatbotService = Depends(get_service)):
    await svc.delete_session(session_id)


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(message_id: int, svc: ChatbotService = Depends(get_service)):
    await svc.delete_message(message_id)


# ── Chat ─────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, svc: ChatbotService = Depends(get_service)):
    try:
        data = await svc.chat(req.session_id, req.user_id, req.message)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Image search ─────────────────────────────────────────────────

@router.post("/search/image-url", response_model=ImageSearchResponse)
async def search_by_image_url(req: ImageSearchRequest, svc: ChatbotService = Depends(get_service)):
    """Tìm sản phẩm tương tự bằng URL ảnh."""
    try:
        products = await svc.search_by_image_url(req.image_url, req.top_k)
        return {"success": True, "products": products}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/image-upload", response_model=ImageSearchResponse)
async def search_by_image_upload(
    file: UploadFile = File(...),
    top_k: int = Query(default=5, ge=1, le=20),
    svc: ChatbotService = Depends(get_service),
):
    """Tìm sản phẩm tương tự bằng upload ảnh trực tiếp."""
    try:
        image_bytes = await file.read()
        products    = await svc.search_by_image_bytes(image_bytes, top_k)
        return {"success": True, "products": products}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Admin: sync Firebase → Neon ──────────────────────────────────

@router.post("/admin/sync-products")
async def sync_products(svc: ChatbotService = Depends(get_service)):
    """
    Đọc toàn bộ sản phẩm Firebase → embed → lưu Neon.
    Chạy 1 lần khi setup hoặc khi thêm sản phẩm mới hàng loạt.
    """
    result = await sync_all_products(svc.embed_repo)
    return {"success": True, **result}