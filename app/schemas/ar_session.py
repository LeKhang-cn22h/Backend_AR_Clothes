from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ARSessionCreate(BaseModel):
    user_id: Optional[int] = None
    garment_id: int
    firestore_product_id: Optional[str] = None
    duration_seconds: Optional[int] = None
    converted: bool = False


class ARSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int]
    garment_id: int
    firestore_product_id: Optional[str]
    duration_seconds: Optional[int]
    converted: bool
    created_at: datetime
    is_deleted: bool = False


class ARSessionStatsResponse(BaseModel):
    total_sessions: int
    total_converted: int
    conversion_rate: float
    top_garments: list[dict]
