from datetime import datetime
from typing import Optional,Literal
from pydantic import BaseModel, ConfigDict, field_validator
addressType=Literal["Nhà riêng", "Cơ quan", "Khác"]
ADDRESS_TYPES=["Nhà riêng", "Cơ quan", "Khác"]
class AddressCreate(BaseModel):
    full_name: str
    phone: str
    address_type:addressType="Nhà riêng"
    address: str
    city: Optional[str] = None
    district: Optional[str] = None
    ward: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_default: bool = False

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        import re
        if not re.match(r'^[0-9]{10,11}$', v.strip()):
            raise ValueError('SĐT không hợp lệ (10-11 số)')
        return v.strip()

class AddressUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address_type: Optional[addressType] = None
    address: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    ward: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_default: Optional[bool] = None


class AddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    full_name: str
    phone: str
    address_type: str
    address: str
    city: Optional[str]
    district: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    ward: Optional[str]
    is_default: bool
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
