from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class WishlistCreate(BaseModel):
    user_id: int
    firestore_product_id: str
    garment_id: Optional[int] = None


class WishlistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    firestore_product_id: str
    garment_id: Optional[int]
    created_at: datetime
    is_deleted: bool = False


class WishlistCheckResponse(BaseModel):
    is_wishlisted: bool
    wishlist_id: Optional[int] = None
