from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ── Products ────────────────────────────────────────────────────
class ProductOut(BaseModel):
    id:     str
    name:   str
    price:  int
    images: str          # JSON string — frontend parse
    brand:  str
    score:  Optional[float] = 0


# ── Messages ────────────────────────────────────────────────────
class MessageIn(BaseModel):
    role:    str
    content: str

class MessageOut(BaseModel):
    id:                 int
    role:               str
    content:            str
    suggested_products: Optional[str] = None
    image_url:          Optional[str] = None
    created_at:         datetime

    class Config:
        from_attributes = True


# ── Sessions ────────────────────────────────────────────────────
class SessionCreate(BaseModel):
    user_id: int
    title:   Optional[str] = "Cuộc trò chuyện mới"

class SessionOut(BaseModel):
    id:         int
    user_id:    int
    title:      str
    created_at: datetime
    updated_at: datetime
    messages:   list[MessageOut] = []

    class Config:
        from_attributes = True

class SessionSummary(BaseModel):
    id:         int
    title:      str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Chat request / response ──────────────────────────────────────
class ChatRequest(BaseModel):
    session_id:          int
    user_id:             int
    message:             str
    image_url:           Optional[str] = None   # tìm kiếm bằng ảnh

class ChatResponse(BaseModel):
    success: bool
    data: ChatResponseData

class ChatResponseData(BaseModel):
    message:           str
    suggested_products: list[ProductOut] = []
    session_id:        int


# ── Image search ─────────────────────────────────────────────────
class ImageSearchRequest(BaseModel):
    image_url: str
    top_k:     Optional[int] = 5

class ImageSearchResponse(BaseModel):
    success:  bool
    products: list[ProductOut] = []