from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ProductViewCreate(BaseModel):
    user_id: Optional[int] = None
    firestore_product_id: str
    session_id: Optional[str] = None
    source: Optional[str] = None


class ProductViewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int]
    firestore_product_id: str
    session_id: Optional[str]
    source: Optional[str]
    created_at: datetime
    is_deleted: bool = False


class ProductViewCountResponse(BaseModel):
    firestore_product_id: str
    view_count: int


class TopProductResponse(BaseModel):
    firestore_product_id: str
    view_count: int
