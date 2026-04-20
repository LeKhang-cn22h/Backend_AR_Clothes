# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class GarmentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    item_index: Optional[int] = None


class GarmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    item_index: Optional[int] = None


class GarmentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    model_url: str
    public_id: str
    item_index: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LensLinkResponse(BaseModel):
    lens_url: str
    model_url: str
    product_id: int