from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from repositories.chat_repository import ChatRepository
from repositories.embedding_repository import EmbeddingRepository
from services.chatbot_service import ChatbotService
from services.embedding_service import sync_all_products
from schemas.chatbot import (
    ChatRequest,
    ChatResponse,
    SessionCreate,
    SessionOut,
    SessionSummary,
)
from core.limiter import limiter

router = APIRouter(prefix="/api/chatbot", tags=["Chatbot"])


def get_service(db: AsyncSession = Depends(get_db)) -> ChatbotService:
    return ChatbotService(ChatRepository(db), EmbeddingRepository(db))


# ── Sessions ──────────────────────────────────────────────────────

@router.post("/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_session(payload: SessionCreate, svc: ChatbotService = Depends(get_service)):
    return await svc.create_session(payload.user_id, payload.title)


@router.get("/sessions", response_model=list[SessionSummary])
@limiter.limit("120/minute")
async def get_sessions(
    user_id: int = Query(...),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    svc: ChatbotService = Depends(get_service),
):
    return await svc.get_sessions(user_id, skip, limit)


@router.get("/sessions/{session_id}", response_model=SessionOut)
@limiter.limit("120/minute")
async def get_session(session_id: int, svc: ChatbotService = Depends(get_service)):
    session = await svc.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session không tồn tại")
    return session


@router.patch("/sessions/{session_id}/title")
@limiter.limit("10/minute")
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
@limiter.limit("10/minute")
async def delete_session(session_id: int, svc: ChatbotService = Depends(get_service)):
    await svc.delete_session(session_id)


# ── Messages ──────────────────────────────────────────────────────

@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_message(message_id: int, svc: ChatbotService = Depends(get_service)):
    await svc.delete_message(message_id)


# ── Chat ──────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat(req: ChatRequest, svc: ChatbotService = Depends(get_service)):
    try:
        data = await svc.chat(req.session_id, req.user_id, req.message)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Admin ─────────────────────────────────────────────────────────

@router.post("/admin/sync-products")
@limiter.limit("10/minute")
async def sync_products(svc: ChatbotService = Depends(get_service)):
    result = await sync_all_products(svc.embed_repo)
    return {"success": True, **result}


@router.get("/admin/embeddings/stats")
@limiter.limit("120/minute")
async def get_embedding_stats(svc: ChatbotService = Depends(get_service)):
    return await svc.get_embedding_stats()


@router.get("/admin/embeddings")
@limiter.limit("120/minute")
async def get_embeddings(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    search: str = Query(default=""),
    svc: ChatbotService = Depends(get_service),
):
    return await svc.get_embeddings(skip, limit, search)

@router.delete("/admin/embeddings/{firestore_product_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("120/minute")
async def delete_embedding(firestore_product_id: str, svc: ChatbotService = Depends(get_service)):
    await svc.delete_embedding(firestore_product_id)