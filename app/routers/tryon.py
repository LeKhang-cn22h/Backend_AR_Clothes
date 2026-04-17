# -*- coding: utf-8 -*-
import base64
import io
import time
from asyncio import get_event_loop

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from PIL import Image

from dependencies import get_catvton_service
from services.catvton import CatVTONService
import services.cloudinary_service as cloud

router = APIRouter(prefix="/tryon")

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_CLOTH_TYPES = {"upper", "lower", "overall"}


def _validate_image(file: UploadFile, field: str):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"{field} phai la image/jpeg, image/png hoac image/webp",
        )


@router.post("")
async def tryon(
    person: UploadFile,
    cloth: UploadFile,
    cloth_type: str = Form(default="upper"),
    num_steps: int = Form(default=50),
    guidance: float = Form(default=2.5),
    seed: int = Form(default=42),
    service: CatVTONService = Depends(get_catvton_service),
):
    _validate_image(person, "person")
    _validate_image(cloth, "cloth")

    if cloth_type not in ALLOWED_CLOTH_TYPES:
        raise HTTPException(
            status_code=400,
            detail="cloth_type phai la upper, lower hoac overall",
        )

    person_bytes = await person.read()
    cloth_bytes = await cloth.read()

    person_image = Image.open(io.BytesIO(person_bytes))
    cloth_image = Image.open(io.BytesIO(cloth_bytes))

    loop = get_event_loop()
    try:
        result: Image.Image = await loop.run_in_executor(
            None,
            lambda: service.run(
                person_image, cloth_image, cloth_type, num_steps, guidance, seed
            ),
        )
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            raise HTTPException(status_code=503, detail="GPU het bo nho, thu lai sau")
        raise HTTPException(status_code=500, detail=f"Loi xu ly anh: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Loi xu ly anh: {e}")

    width, height = result.size
    timestamp = int(time.time())
    public_id = f"tryon_results/{timestamp}_{seed}"

    try:
        upload_info = cloud.upload_image(result, folder="tryon_results", public_id=public_id)
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
