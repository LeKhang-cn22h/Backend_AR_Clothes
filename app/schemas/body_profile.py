from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BodyProfileCreate(BaseModel):
    height: Optional[Decimal] = Field(default=None, ge=0)
    weight: Optional[Decimal] = Field(default=None, ge=0)
    chest: Optional[Decimal] = Field(default=None, ge=0)
    waist: Optional[Decimal] = Field(default=None, ge=0)
    hip: Optional[Decimal] = Field(default=None, ge=0)
    shoulder: Optional[Decimal] = Field(default=None, ge=0)
    arm_length: Optional[Decimal] = Field(default=None, ge=0)
    inseam: Optional[Decimal] = Field(default=None, ge=0)
    gender: str = "neutral"


class BodyProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    height: Optional[Decimal]
    weight: Optional[Decimal]
    chest: Optional[Decimal]
    waist: Optional[Decimal]
    hip: Optional[Decimal]
    shoulder: Optional[Decimal]
    arm_length: Optional[Decimal]
    inseam: Optional[Decimal]
    gender: str
    beta_hash: Optional[str]
    created_at: datetime
