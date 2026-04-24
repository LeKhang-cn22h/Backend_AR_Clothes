# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class GarmentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    item_index: Optional[int] = None
    category_id: Optional[int] = None
    firestore_product_id: Optional[str] = None


class GarmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    item_index: Optional[int] = None
    category_id: Optional[int] = None
    firestore_product_id: Optional[str] = None


class GarmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    model_url: str
    public_id: str
    local_url: Optional[str]
    item_index: Optional[int]
    category_id: Optional[int]
    firestore_product_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class LensLinkResponse(BaseModel):
    lens_url: str
    model_url: str
    product_id: int
