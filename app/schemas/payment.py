from pydantic import BaseModel
from typing import Optional

class StripeCreateRequest(BaseModel):
    order_id: str
    amount: float
    order_desc: Optional[str] = "Thanh toan don hang GlowUp"

class StripeCreateResponse(BaseModel):
    payment_url: str