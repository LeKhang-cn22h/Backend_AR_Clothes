import asyncio
import hashlib
import logging
import os
import tempfile

import cloudinary.uploader
import cv2
import numpy as np
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from repositories.body_profile_repository import BodyProfileRepository
from repositories.garment_drape_repository import GarmentDrapeRepository
from repositories.garment_repository import GarmentRepository
from repositories.photo_avatar_repository import PhotoAvatarRepository
from repositories.photo_tryon_session_repository import PhotoTryonSessionRepository
from repositories.user_repository import UserRepository
from schemas.body_profile import BodyProfileCreate, BodyProfileResponse
from schemas.fit_assessment import (
    FaceReconstructResponse,
    FitAssessmentRequest,
    FitAssessmentResult,
    LandmarksResponse,
    MergeFaceRequest,
    MergeFaceResponse,
)
from schemas.photo_avatar import PhotoAvatarCreate, PhotoAvatarResponse
from schemas.photo_tryon_session import (
    PhotoTryonSessionResponse,
    TryonRequest,
    TryonResponse,
)
from services.body_profile_service import BodyProfileService
from services.fit_assessment_service import FitAssessmentService
from services.ml.body_landmarks_service import compute_landmarks_from_beta
from services.ml.deca_service import get_deca_service
from services.ml.head_body_merge_service import (
    get_neck_joint_position,
    merge_head_body,
)
from services.photo_avatar_service import PhotoAvatarService
from services.photo_tryon_session_service import PhotoTryonSessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/photo-tryon", tags=["Photo Try-On"])


# ══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY INJECTION
# ══════════════════════════════════════════════════════════════════════════════

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


def get_fit_assessment_service(
    db: AsyncSession = Depends(get_db),
) -> FitAssessmentService:
    return FitAssessmentService(BodyProfileRepository(db), GarmentRepository(db))


# ══════════════════════════════════════════════════════════════════════════════
# CLOUDINARY HELPER (face GLB bytes → URL)
# ══════════════════════════════════════════════════════════════════════════════

def _upload_glb_bytes_to_cloudinary(
    glb_bytes: bytes, folder: str, public_id: str
) -> str:
    """Ghi bytes ra file tạm rồi upload — Cloudinary SDK ưa file path hơn."""
    tmp = tempfile.NamedTemporaryFile(suffix=".glb", delete=False)
    try:
        tmp.write(glb_bytes)
        tmp.close()
        result = cloudinary.uploader.upload(
            tmp.name,
            resource_type="raw",
            folder=folder,
            public_id=public_id,
            overwrite=True,
        )
        return result["secure_url"]
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


# ══════════════════════════════════════════════════════════════════════════════
# EXISTING ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# NEW: FACE RECONSTRUCTION (DECA)
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/face/reconstruct",
    response_model=FaceReconstructResponse,
    status_code=status.HTTP_201_CREATED,
)
async def reconstruct_face(
    image: UploadFile = File(...),
    user_id: int = Query(..., ge=1),
):
    """Upload selfie → DECA face reconstruction → upload GLB → trả URL."""
    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty image upload")

    arr = np.frombuffer(raw, dtype=np.uint8)
    image_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise HTTPException(status_code=400, detail="Cannot decode image")

    deca = get_deca_service()
    try:
        result = await deca.reconstruct_face(image_bgr)
    except ValueError as e:
        # No face detected → 422 Unprocessable Entity
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("DECA reconstruction failed")
        raise HTTPException(status_code=500, detail=f"DECA error: {e}")

    public_id = f"face_{user_id}_{hashlib.md5(raw).hexdigest()[:12]}"
    loop = asyncio.get_event_loop()
    face_glb_url = await loop.run_in_executor(
        None,
        _upload_glb_bytes_to_cloudinary,
        result["glb_bytes"],
        "face_meshes",
        public_id,
    )

    return FaceReconstructResponse(
        face_glb_url=face_glb_url,
        face_params=result["params"],
    )


# ══════════════════════════════════════════════════════════════════════════════
# NEW: HEAD-BODY MERGE
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/avatar/{avatar_id}/merge-face",
    response_model=MergeFaceResponse,
)
async def merge_face_into_avatar(
    avatar_id: int,
    payload: MergeFaceRequest,
    user_id: int = Query(..., ge=1),
    avatar_service: PhotoAvatarService = Depends(get_photo_avatar_service),
    db: AsyncSession = Depends(get_db),
):
    """
    Ghép head GLB (Cloudinary URL) vào body GLB của avatar.

    Bước:
      1. Load avatar — phải có body_glb_url (status="ready")
      2. Lấy beta + gender từ body_profile để tính neck joint
      3. Tải face GLB từ URL → bytes
      4. merge_head_body → upload Cloudinary
      5. Cập nhật avatar.head_glb_url, merged_glb_url, neck_joint
    """
    avatar = await avatar_service.get_avatar(avatar_id, user_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Khong tim thay avatar")
    if not avatar.body_glb_url:
        raise HTTPException(
            status_code=409,
            detail="Avatar chưa có body GLB — tạo body trước khi merge",
        )
    if not avatar.body_profile_id:
        raise HTTPException(
            status_code=409, detail="Avatar không có body_profile để xác định neck"
        )

    body_profile_repo = BodyProfileRepository(db)
    profile = await body_profile_repo.get_by_id(avatar.body_profile_id)
    if not profile or not profile.beta_cache:
        raise HTTPException(
            status_code=409,
            detail="Body profile chưa có beta_cache — chưa thể tính neck joint",
        )

    beta = (profile.beta_cache or {}).get("betas")
    if not beta:
        raise HTTPException(
            status_code=409, detail="beta_cache không hợp lệ"
        )

    # Tải face GLB từ Cloudinary URL
    from urllib.request import urlopen
    loop = asyncio.get_event_loop()

    def _fetch_bytes(url: str) -> bytes:
        with urlopen(url) as r:
            return r.read()

    try:
        face_bytes = await loop.run_in_executor(None, _fetch_bytes, payload.face_glb_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot fetch face GLB: {e}")

    # Tính neck joint từ SMPL-X
    neck_pos = await loop.run_in_executor(
        None, get_neck_joint_position, beta, profile.gender
    )

    # Merge + upload
    public_id = f"merged_{avatar_id}_{hashlib.md5(payload.face_glb_url.encode()).hexdigest()[:12]}"
    merged_url = await merge_head_body(
        body_glb_url=avatar.body_glb_url,
        head_glb_bytes=face_bytes,
        neck_joint_pos=neck_pos,
        public_id=public_id,
    )

    # Cập nhật DB
    avatar_repo = PhotoAvatarRepository(db)
    await avatar_repo.update_urls(
        avatar_id=avatar_id,
        head_glb_url=payload.face_glb_url,
        merged_glb_url=merged_url,
        neck_joint={"x": float(neck_pos[0]), "y": float(neck_pos[1]), "z": float(neck_pos[2])},
    )
    await avatar_repo.update_status(avatar_id=avatar_id, status="ready")

    return MergeFaceResponse(merged_glb_url=merged_url, status="ready")


# ══════════════════════════════════════════════════════════════════════════════
# NEW: FIT ASSESSMENT
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/fit-assessment",
    response_model=FitAssessmentResult,
)
async def fit_assessment(
    payload: FitAssessmentRequest,
    service: FitAssessmentService = Depends(get_fit_assessment_service),
):
    return await service.assess(
        body_profile_id=payload.body_profile_id,
        garment_id=payload.garment_id,
        size_label=payload.size_label,
    )


# ══════════════════════════════════════════════════════════════════════════════
# NEW: BODY LANDMARKS
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/avatar/{avatar_id}/landmarks",
    response_model=LandmarksResponse,
)
async def get_avatar_landmarks(
    avatar_id: int,
    user_id: int = Query(..., ge=1),
    avatar_service: PhotoAvatarService = Depends(get_photo_avatar_service),
    db: AsyncSession = Depends(get_db),
):
    avatar = await avatar_service.get_avatar(avatar_id, user_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="Khong tim thay avatar")
    if not avatar.body_profile_id:
        raise HTTPException(
            status_code=409, detail="Avatar không có body_profile"
        )

    profile = await BodyProfileRepository(db).get_by_id(avatar.body_profile_id)
    if not profile or not profile.beta_cache:
        raise HTTPException(
            status_code=409,
            detail="Body profile chưa có beta_cache — chưa tạo body mesh xong",
        )
    beta = (profile.beta_cache or {}).get("betas")
    if not beta:
        raise HTTPException(status_code=409, detail="beta_cache không hợp lệ")

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, compute_landmarks_from_beta, beta, profile.gender
    )
    return LandmarksResponse(**result)
