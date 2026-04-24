from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from models.conversion_event import ConversionEventType


class ConversionEventCreate(BaseModel):
    user_id: Optional[int] = None
    firestore_product_id: str
    garment_id: Optional[int] = None
    event_type: ConversionEventType
    session_id: Optional[str] = None


class ConversionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int]
    firestore_product_id: str
    garment_id: Optional[int]
    event_type: ConversionEventType
    session_id: Optional[str]
    created_at: datetime
    is_deleted: bool = False


class FunnelResponse(BaseModel):
    view: int
    ar_try_on: int
    add_to_cart: int
    purchase: int
    ar_to_purchase_rate: float


class OverviewResponse(BaseModel):
    view: int
    ar_try_on: int
    add_to_cart: int
    purchase: int
