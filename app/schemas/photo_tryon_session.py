from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, ConfigDict


class PhotoTryonSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int]
    garment_id: int
    person_image_url: Optional[str]
    result_image_url: Optional[str]
    result_public_id: Optional[str]
    cloth_type: str
    selected_size: Optional[str]
    suggested_size: Optional[str]
    fit_warnings: Optional[list[Any]]
    created_at: datetime


class SmartTryonResponse(BaseModel):
    session_id: Optional[int]
    result_image_url: Optional[str]
    public_id: Optional[str]
    width: int
    height: int
    input_type: str  # "full_body" | "face_only"
    suggested_size: Optional[str] = None
    fit_warnings: Optional[list[Any]] = None
    created_at: Optional[str] = None
