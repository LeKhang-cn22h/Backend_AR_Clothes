from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TryonRequest(BaseModel):
    avatar_id: int
    garment_id: int
    selected_size: str


class FitWarning(BaseModel):
    severity: str
    message: str
    delta_cm: float


class TryonResponse(BaseModel):
    session_id: int
    avatar_id: int
    garment_id: int
    selected_size: str
    suggested_size: Optional[str]
    fit_warnings: list[FitWarning]
    garment_drape_glb_url: Optional[str]
    heatmap_glb_url: Optional[str]


class PhotoTryonSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int]
    avatar_id: int
    garment_id: int
    selected_size: str
    suggested_size: Optional[str]
    fit_warnings: Optional[list[FitWarning]]
    created_at: datetime
