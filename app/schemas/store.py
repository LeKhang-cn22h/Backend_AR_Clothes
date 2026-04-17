# -*- coding: utf-8 -*-
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class StoreBase(BaseModel):
    name: str
    description: Optional[str] = None
    address: str
    phone: str
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    is_active: bool = True


class StoreCreate(StoreBase):
    pass


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    is_active: Optional[bool] = None


class StoreResponse(StoreBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
