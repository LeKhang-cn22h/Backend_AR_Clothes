from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from repositories.body_profile_repository import BodyProfileRepository
from repositories.garment_drape_repository import GarmentDrapeRepository
from repositories.garment_repository import GarmentRepository
from repositories.photo_avatar_repository import PhotoAvatarRepository
from repositories.photo_tryon_session_repository import PhotoTryonSessionRepository
from repositories.user_repository import UserRepository
from schemas.body_profile import BodyProfileCreate, BodyProfileResponse
from schemas.photo_avatar import PhotoAvatarCreate, PhotoAvatarResponse
from schemas.photo_tryon_session import (
    PhotoTryonSessionResponse,
    TryonRequest,
    TryonResponse,
)
from services.body_profile_service import BodyProfileService
from services.photo_avatar_service import PhotoAvatarService
from services.photo_tryon_session_service import PhotoTryonSessionService

router = APIRouter(prefix="/photo-tryon", tags=["Photo Try-On"])


def get_body_profile_service(
    db: AsyncSession = Depends(get_db),
) -> BodyProfileService:
    return BodyProfileService(BodyProfileRepository(db), UserRepository(db))


def get_photo_avatar_service(
    db: AsyncSession = Depends(get_db),
) -> PhotoAvatarService:
    return PhotoAvatarService(
        PhotoAvatarRepository(db),
        UserRepository(db),
        BodyProfileRepository(db),
    )


def get_tryon_session_service(
    db: AsyncSession = Depends(get_db),
) -> PhotoTryonSessionService:
    return PhotoTryonSessionService(
        PhotoTryonSessionRepository(db),
        PhotoAvatarRepository(db),
        GarmentRepository(db),
        BodyProfileRepository(db),
        GarmentDrapeRepository(db),
    )


@router.post(
    "/body-profile",
    response_model=BodyProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_or_update_body_profile(
    payload: BodyProfileCreate,
    user_id: int = Query(..., ge=1),
    service: BodyProfileService = Depends(get_body_profile_service),
):
    return await service.create_or_update_profile(user_id, payload)


@router.post(
    "/avatar/generate",
    response_model=PhotoAvatarResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_avatar(
    payload: PhotoAvatarCreate,
    user_id: int = Query(..., ge=1),
    service: PhotoAvatarService = Depends(get_photo_avatar_service),
):
    return await service.create_avatar_job(user_id, payload.body_profile_id)


@router.get("/avatar/{avatar_id}", response_model=PhotoAvatarResponse)
async def get_avatar(
    avatar_id: int,
    user_id: int = Query(..., ge=1),
    service: PhotoAvatarService = Depends(get_photo_avatar_service),
):
    avatar = await service.get_avatar(avatar_id, user_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Khong tim thay avatar")
    return avatar


@router.post("/tryon", response_model=TryonResponse)
async def create_tryon(
    payload: TryonRequest,
    user_id: int = Query(..., ge=1),
    service: PhotoTryonSessionService = Depends(get_tryon_session_service),
):
    return await service.create_tryon_session(
        user_id=user_id,
        avatar_id=payload.avatar_id,
        garment_id=payload.garment_id,
        selected_size=payload.selected_size,
    )


@router.get("/sessions", response_model=list[PhotoTryonSessionResponse])
async def get_user_sessions(
    user_id: int = Query(..., ge=1),
    service: PhotoTryonSessionService = Depends(get_tryon_session_service),
):
    return await service.get_user_sessions(user_id)
