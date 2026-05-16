from pydantic import BaseModel
from typing import Optional

class VNPayCreateRequest(BaseModel):
    order_id:str
    mount:float
    order_desc:Optional[str] = "Thanh toán đơn hàng"
    bank_code:Optional[str] = None

class VNPayCreateResponse(BaseModel):
    payment_url: str
