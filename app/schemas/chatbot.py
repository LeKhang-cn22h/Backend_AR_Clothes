from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ProductOut(BaseModel):
    id:     str
    name:   str
    price:  int
    images: str
    brand:  str
    score:  Optional[float] = 0


class MessageOut(BaseModel):
    id:                 int
    role:               str
    content:            str
    suggested_products: Optional[str] = None
    created_at:         datetime

    class Config:
        from_attributes = True


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


class ChatRequest(BaseModel):
    session_id: int
    user_id:    int
    message:    str


class ChatResponseData(BaseModel):
    message:            str
    suggested_products: list[ProductOut] = []
    session_id:         int


class ChatResponse(BaseModel):
    success: bool
    data:    ChatResponseData