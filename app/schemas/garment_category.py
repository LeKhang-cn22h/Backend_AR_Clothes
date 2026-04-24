from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class GarmentCategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None


class GarmentCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class GarmentCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    created_at: datetime
