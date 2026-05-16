from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


class ReviewCreate(BaseModel):
    user_id: int
    firestore_product_id: str
    rating: int
    comment: Optional[str] = None
    media_urls: Optional[list[str]] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("Rating phai trong khoang 1-5")
        return v


class ReviewUpdate(BaseModel):
    rating: Optional[int] = None
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 5):
            raise ValueError("Rating phai trong khoang 1-5")
        return v


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    firestore_product_id: str
    rating: int
    comment: Optional[str]
    media_urls: Optional[list[str]] = None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None


class ReviewStatsResponse(BaseModel):
    avg_rating: float
    total_reviews: int
    distribution: dict[str, int]