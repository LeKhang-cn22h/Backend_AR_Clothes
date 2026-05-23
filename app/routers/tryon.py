import base64
import io
import time
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from repositories.body_profile_repository import BodyProfileRepository
from repositories.garment_repository import GarmentRepository
from services.fit_assessment_service import FitAssessmentService
import services.fitdit_service as fitdit_service
import services.cloudinary_service as cloud

router = APIRouter(prefix="/tryon")

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_CLOTH_TYPES = {"upper", "lower", "overall"}
ALLOWED_RESOLUTIONS = {"768x1024", "1152x1536", "1536x2048"}


def _validate_image(file: UploadFile, field: str):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"{field} phai la image/jpeg, image/png hoac image/webp",
        )


def _validate_common(cloth_type: str, resolution: str):
    if cloth_type not in ALLOWED_CLOTH_TYPES:
        raise HTTPException(
            status_code=400,
            detail="cloth_type phai la upper, lower hoac overall",
        )
    if resolution not in ALLOWED_RESOLUTIONS:
        raise HTTPException(
            status_code=400,
            detail="resolution phai la 768x1024, 1152x1536 hoac 1536x2048",
        )


# ════════════════════════════════════════════════════════════════════
# POST /tryon
# ════════════════════════════════════════════════════════════════════
@router.post("")
async def tryon(
    person: UploadFile,
    cloth: UploadFile,
    cloth_type: str = Form(default="upper"),
    num_steps: int = Form(default=15),
    guidance: float = Form(default=2.0),
    seed: int = Form(default=42),
    resolution: str = Form(default="768x1024"),
):
    _validate_image(person, "person")
    _validate_image(cloth, "cloth")
    _validate_common(cloth_type, resolution)

    person_bytes = await person.read()
    cloth_bytes = await cloth.read()

    person_image = Image.open(io.BytesIO(person_bytes)).convert("RGB")
    cloth_image = Image.open(io.BytesIO(cloth_bytes)).convert("RGB")

    try:
        result: Image.Image = await fitdit_service.try_on_from_pil_async(
            person_img=person_image,
            garment_img=cloth_image,
            category=cloth_type,
            num_steps=num_steps,
            guidance_scale=guidance,
            seed=seed,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Loi FitDiT: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Loi xu ly anh: {e}")

    width, height = result.size
    timestamp = int(time.time())
    public_id = f"tryon_results/{timestamp}_{seed}"

    try:
        upload_info = cloud.upload_image(
            result,
            folder="tryon_results",
            public_id=public_id,
        )
        return {
            "image_url": upload_info["url"],
            "public_id": upload_info["public_id"],
            "width": width,
            "height": height,
            "created_at": upload_info["created_at"],
        }
    except Exception:
        buf = io.BytesIO()
        result.save(buf, format="JPEG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return {
            "image_url": None,
            "public_id": None,
            "width": width,
            "height": height,
            "created_at": None,
            "image_base64": f"data:image/jpeg;base64,{b64}",
            "warning": "Upload Cloudinary that bai, tra ve anh dang base64",
        }


# ════════════════════════════════════════════════════════════════════
# Helper download cloth image
# ════════════════════════════════════════════════════════════════════
async def _download_cloth_image(url: str) -> Image.Image:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGB")


# ════════════════════════════════════════════════════════════════════
# POST /tryon/smart
# ════════════════════════════════════════════════════════════════════
@router.post("/smart")
async def tryon_smart(
    person: UploadFile,
    garment_id: int = Form(...),
    user_id: Optional[int] = Form(default=None),
    cloth_type: str = Form(default="upper"),
    num_steps: int = Form(default=20),
    guidance: float = Form(default=2.0),
    seed: int = Form(default=42),
    resolution: str = Form(default="768x1024"),
    db: AsyncSession = Depends(get_db),
):
    _validate_image(person, "person")
    _validate_common(cloth_type, resolution)

    person_bytes = await person.read()
    person_image = Image.open(io.BytesIO(person_bytes)).convert("RGB")

    # 1. Load garment
    garment_repo = GarmentRepository(db)
    garment = await garment_repo.get_by_id(garment_id)
    if not garment:
        raise HTTPException(status_code=404, detail="Khong tim thay garment")
    if not garment.cloth_image_url:
        raise HTTPException(status_code=400, detail="Garment chua co cloth_image_url")

    # 2. Download cloth image
    try:
        cloth_image = await _download_cloth_image(garment.cloth_image_url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Khong tai duoc cloth image: {e}")

    # 3. Fit assessment (optional)
    suggested_size: Optional[str] = None
    fit_warnings: Optional[list] = None

    if user_id is not None:
        body_repo = BodyProfileRepository(db)
        profile = await body_repo.get_by_user_id(user_id)
        if profile and isinstance(getattr(garment, "sizes", None), dict):
            assess_service = FitAssessmentService(body_repo, garment_repo)
            try:
                assessment = await assess_service.assess(
                    body_profile_id=profile.id,
                    garment_id=garment_id,
                )
                suggested_size = assessment.get("size_suggestion")
                warnings: list = []
                for region in ("chest", "waist", "hip"):
                    info = assessment.get(f"{region}_fit") or {}
                    s = info.get("status")
                    if s in ("tight", "loose"):
                        warnings.append({
                            "region": region,
                            "status": s,
                            "diff_cm": info.get("diff_cm"),
                        })
                fit_warnings = warnings or None
            except HTTPException:
                pass

    # 4. Run FitDiT
    try:
        result: Image.Image = await fitdit_service.try_on_from_pil_async(
            person_img=person_image,
            garment_img=cloth_image,
            category=cloth_type,
            num_steps=num_steps,
            guidance_scale=guidance,
            seed=seed,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Loi FitDiT: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Loi xu ly anh: {e}")

    width, height = result.size

    # 5. Upload result lên Cloudinary
    timestamp = int(time.time())
    upload_info = None
    try:
        upload_info = cloud.upload_image(
            result,
            folder="tryon_results",
            public_id=f"tryon_results/{timestamp}_{seed}_{garment_id}",
        )
    except Exception as e:
        print(f"[smart] Upload Cloudinary that bai: {e}")

    return {
        "result_image_url": upload_info["url"] if upload_info else None,
        "public_id": upload_info["public_id"] if upload_info else None,
        "width": width,
        "height": height,
        "suggested_size": suggested_size,
        "fit_warnings": fit_warnings,
        "created_at": upload_info["created_at"] if upload_info else None,
    }