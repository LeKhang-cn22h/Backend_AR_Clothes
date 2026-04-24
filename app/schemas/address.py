from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AddressCreate(BaseModel):
    full_name: str
    phone: str
    address: str
    city: Optional[str] = None
    district: Optional[str] = None
    ward: Optional[str] = None
    is_default: bool = False


class AddressUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    ward: Optional[str] = None
    is_default: Optional[bool] = None


class AddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    full_name: str
    phone: str
    address: str
    city: Optional[str]
    district: Optional[str]
    ward: Optional[str]
    is_default: bool
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
