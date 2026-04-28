from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PhotoAvatarCreate(BaseModel):
    body_profile_id: Optional[int] = None


class PhotoAvatarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    body_profile_id: Optional[int]
    merged_glb_url: Optional[str]
    status: str
    error_message: Optional[str]
    created_at: datetime
