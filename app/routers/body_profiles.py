from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from repositories.body_profile_repository import BodyProfileRepository
from repositories.user_repository import UserRepository
from schemas.body_profile import BodyProfileCreate, BodyProfileResponse
from services.body_profile_service import BodyProfileService

router = APIRouter(prefix="/body-profiles", tags=["Body Profiles"])


def get_service(db: AsyncSession = Depends(get_db)) -> BodyProfileService:
    return BodyProfileService(
        BodyProfileRepository(db),
        UserRepository(db),
    )


@router.get("", response_model=BodyProfileResponse | None)
async def get_body_profile(
    user_id: int = Query(..., gt=0),
    svc: BodyProfileService = Depends(get_service),
):
    """Lấy body profile của user. Trả None nếu chưa có."""
    return await svc.get_by_user_id(user_id)


@router.post("", response_model=BodyProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_body_profile(
    user_id: int = Query(..., gt=0),
    payload: BodyProfileCreate = ...,
    svc: BodyProfileService = Depends(get_service),
):
    """Tạo mới hoặc cập nhật body profile (upsert theo user_id)."""
    return await svc.create_or_update_profile(user_id, payload)