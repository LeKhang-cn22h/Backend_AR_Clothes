"""
routers/tryon_router.py
-----------------------
Xử lý ghép ảnh với async polling — tránh timeout ngrok.

Flow:
    1. POST /tryon hoặc /tryon/catalog → trả job_id ngay
    2. GET  /tryon/status/{job_id}     → poll mỗi 5s cho đến khi done/failed
    3. GET  /tryon/history             → lịch sử ghép ảnh của user

Endpoints:
    POST /tryon                    → upload 2 ảnh trực tiếp
    POST /tryon/catalog            → cloth lấy từ garment catalog
    GET  /tryon/status/{job_id}    → kiểm tra trạng thái job
    GET  /tryon/history            → lịch sử ghép ảnh
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import time
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Query, UploadFile
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db, AsyncSessionLocal
from repositories.garment_repository import GarmentRepository
from repositories.tryon_history_repository import TryonHistoryRepository
import services.fitdit_service as fitdit_service
import services.cloudinary_service as cloud
from core.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tryon", tags=["tryon"])

ALLOWED_TYPES       = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_CLOTH_TYPES = {"upper", "lower", "overall"}
ALLOWED_RESOLUTIONS = {"768x1024", "1152x1536", "1536x2048"}

# ══════════════════════════════════════════════════════════════════════════════
# IN-MEMORY JOB STORE
# ══════════════════════════════════════════════════════════════════════════════

# Format: {job_id: {status, result_image_url, error, ...}}
# status: queued | processing | done | failed
_jobs: dict = {}

# Tự dọn job cũ hơn 1 giờ để tránh leak memory
_JOB_TTL_S = 3600


def _cleanup_old_jobs() -> None:
    now = time.time()
    expired = [jid for jid, j in _jobs.items() if now - j.get("created_at", now) > _JOB_TTL_S]
    for jid in expired:
        del _jobs[jid]
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired tryon jobs")


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATORS
# ══════════════════════════════════════════════════════════════════════════════

def _validate_image(file: UploadFile, field: str) -> None:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"{field} phải là image/jpeg, image/png hoặc image/webp",
        )


def _validate_params(cloth_type: str, resolution: str) -> None:
    if cloth_type not in ALLOWED_CLOTH_TYPES:
        raise HTTPException(
            status_code=400,
            detail="cloth_type phải là upper, lower hoặc overall",
        )
    if resolution not in ALLOWED_RESOLUTIONS:
        raise HTTPException(
            status_code=400,
            detail="resolution phải là 768x1024, 1152x1536 hoặc 1536x2048",
        )


# ══════════════════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ══════════════════════════════════════════════════════════════════════════════

async def _run_fitdit(
    person_image: Image.Image,
    cloth_image: Image.Image,
    cloth_type: str,
    num_steps: int,
    guidance: float,
    seed: int,
) -> Image.Image:
    return await fitdit_service.try_on_from_pil_async(
        person_img=person_image,
        garment_img=cloth_image,
        category=cloth_type,
        num_steps=num_steps,
        guidance_scale=guidance,
        seed=seed,
    )


def _upload_or_base64(result: Image.Image, folder: str, public_id: str) -> dict:
    """Upload lên Cloudinary; fallback base64 nếu thất bại."""
    try:
        info = cloud.upload_image(result, folder=folder, public_id=public_id)
        return {
            "result_image_url": info["url"],
            "public_id":        info["public_id"],
            "created_at":       info["created_at"],
            "fallback":         False,
        }
    except Exception:
        buf = io.BytesIO()
        result.save(buf, format="JPEG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return {
            "result_image_url": None,
            "public_id":        None,
            "created_at":       None,
            "image_base64":     f"data:image/jpeg;base64,{b64}",
            "fallback":         True,
            "warning":          "Upload Cloudinary thất bại, trả về ảnh dạng base64",
        }


async def _save_history(
    repo: TryonHistoryRepository,
    upload: dict,
    result: Image.Image,
    cloth_type: str,
    seed: int,
    num_steps: int,
    guidance: float,
    resolution: str,
    user_id: Optional[int] = None,
    garment_id: Optional[int] = None,
) -> None:
    if upload.get("fallback"):
        return
    try:
        await repo.create({
            "user_id":          user_id,
            "garment_id":       garment_id,
            "result_image_url": upload["result_image_url"],
            "public_id":        upload["public_id"],
            "width":            result.size[0],
            "height":           result.size[1],
            "cloth_type":       cloth_type,
            "seed":             seed,
            "num_steps":        num_steps,
            "guidance":         guidance,
            "resolution":       resolution,
        })
    except Exception as e:
        logger.warning(f"Lưu tryon_history thất bại: {e}")


async def _download_image(url: str) -> Image.Image:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGB")


# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND JOB RUNNER
# ══════════════════════════════════════════════════════════════════════════════

async def _run_tryon_job(
    job_id: str,
    person_image: Image.Image,
    cloth_image: Image.Image,
    cloth_type: str,
    num_steps: int,
    guidance: float,
    seed: int,
    resolution: str,
    user_id: Optional[int],
    garment_id: Optional[int],
) -> None:
    """
    Chạy inference trong background.
    Cập nhật _jobs[job_id] liên tục để client poll được.
    """
    try:
        _jobs[job_id]["status"] = "processing"
        logger.info(f"[{job_id[:8]}] Bắt đầu inference: {cloth_type} steps={num_steps}")

        result = await _run_fitdit(
            person_image, cloth_image,
            cloth_type, num_steps, guidance, seed,
        )

        timestamp = int(time.time())
        upload = _upload_or_base64(
            result,
            "tryon_results",
            f"tryon_results/{timestamp}_{seed}_{job_id[:8]}",
        )

        _jobs[job_id].update({
            "status":           "done",
            "result_image_url": upload.get("result_image_url"),
            "public_id":        upload.get("public_id"),
            "image_base64":     upload.get("image_base64"),
            "width":            result.size[0],
            "height":           result.size[1],
            "garment_id":       garment_id,
            "warning":          upload.get("warning"),
            "finished_at":      time.time(),
        })

        logger.info(f"[{job_id[:8]}] Done — {upload.get('result_image_url') or 'base64'}")

        # Lưu history dùng session mới (session gốc đã đóng)
        async with AsyncSessionLocal() as db:
            repo = TryonHistoryRepository(db)
            await _save_history(
                repo, upload, result,
                cloth_type, seed, num_steps, guidance, resolution,
                user_id=user_id,
                garment_id=garment_id,
            )

    except Exception as e:
        logger.error(f"[{job_id[:8]}] Inference thất bại: {e}")
        _jobs[job_id].update({
            "status":      "failed",
            "error":       str(e),
            "finished_at": time.time(),
        })


# ══════════════════════════════════════════════════════════════════════════════
# POST /tryon — upload trực tiếp 2 ảnh
# ══════════════════════════════════════════════════════════════════════════════

@router.post("")
@limiter.limit("10/minute")
async def tryon(
    background_tasks: BackgroundTasks,
    person:     UploadFile,
    cloth:      UploadFile,
    user_id:    Optional[int] = Form(default=None),
    cloth_type: str           = Form(default="upper"),
    num_steps:  int           = Form(default=15),
    guidance:   float         = Form(default=2.0),
    seed:       int           = Form(default=42),
    resolution: str           = Form(default="768x1024"),
):
    """
    Ghép ảnh thử đồ — trả job_id ngay, không chờ inference xong.
    Poll GET /tryon/status/{job_id} mỗi 5 giây để lấy kết quả.
    """
    _validate_image(person, "person")
    _validate_image(cloth, "cloth")
    _validate_params(cloth_type, resolution)

    person_image = Image.open(io.BytesIO(await person.read())).convert("RGB")
    cloth_image  = Image.open(io.BytesIO(await cloth.read())).convert("RGB")

    _cleanup_old_jobs()

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status":     "queued",
        "created_at": time.time(),
        "cloth_type": cloth_type,
        "num_steps":  num_steps,
    }

    background_tasks.add_task(
        _run_tryon_job,
        job_id, person_image, cloth_image,
        cloth_type, num_steps, guidance, seed, resolution,
        user_id, None,
    )

    return {
        "job_id":   job_id,
        "status":   "queued",
        "poll_url": f"/tryon/status/{job_id}",
        "message":  "Đang xử lý. Poll /tryon/status/{job_id} mỗi 5 giây.",
    }


# ══════════════════════════════════════════════════════════════════════════════
# POST /tryon/catalog — cloth lấy từ garment catalog
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/catalog")
@limiter.limit("10/minute")
async def tryon_catalog(
    background_tasks: BackgroundTasks,
    person:     UploadFile,
    garment_id: int           = Form(...),
    user_id:    Optional[int] = Form(default=None),
    cloth_type: str           = Form(default="upper"),
    num_steps:  int           = Form(default=15),
    guidance:   float         = Form(default=2.0),
    seed:       int           = Form(default=42),
    resolution: str           = Form(default="768x1024"),
    db: AsyncSession = Depends(get_db),
):
    """
    Ghép ảnh từ catalog — cloth lấy từ garment_id, không cần upload.
    Trả job_id ngay. Poll GET /tryon/status/{job_id} mỗi 5 giây.
    """
    _validate_image(person, "person")
    _validate_params(cloth_type, resolution)

    # Load garment
    garment_repo = GarmentRepository(db)
    garment = await garment_repo.get_by_id(garment_id)
    if not garment:
        raise HTTPException(status_code=404, detail="Không tìm thấy garment")
    if not garment.cloth_image_url:
        raise HTTPException(status_code=400, detail="Garment chưa có cloth_image_url")

    # Download cloth image
    try:
        cloth_image = await _download_image(garment.cloth_image_url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Không tải được cloth image: {e}")

    person_image = Image.open(io.BytesIO(await person.read())).convert("RGB")

    _cleanup_old_jobs()

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status":     "queued",
        "created_at": time.time(),
        "garment_id": garment_id,
        "cloth_type": cloth_type,
        "num_steps":  num_steps,
    }

    background_tasks.add_task(
        _run_tryon_job,
        job_id, person_image, cloth_image,
        cloth_type, num_steps, guidance, seed, resolution,
        user_id, garment_id,
    )

    return {
        "job_id":     job_id,
        "status":     "queued",
        "garment_id": garment_id,
        "poll_url":   f"/tryon/status/{job_id}",
        "message":    "Đang xử lý. Poll /tryon/status/{job_id} mỗi 5 giây.",
    }


# ══════════════════════════════════════════════════════════════════════════════
# GET /tryon/status/{job_id} — poll trạng thái
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/status/{job_id}")
def get_tryon_status(job_id: str):
    """
    Poll endpoint — FE gọi mỗi 5s cho đến khi status = done hoặc failed.

    status values:
        queued     → đã nhận job, chờ chạy
        processing → đang inference trên FitDiT
        done       → xong, có result_image_url hoặc image_base64
        failed     → lỗi, có error message
    """
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job không tồn tại hoặc đã hết hạn")

    elapsed = round(time.time() - job.get("created_at", time.time()), 1)

    if job["status"] == "done":
        return {
            "job_id":           job_id,
            "status":           "done",
            "result_image_url": job.get("result_image_url"),
            "image_base64":     job.get("image_base64"),
            "public_id":        job.get("public_id"),
            "width":            job.get("width"),
            "height":           job.get("height"),
            "garment_id":       job.get("garment_id"),
            "warning":          job.get("warning"),
            "elapsed_s":        elapsed,
        }

    if job["status"] == "failed":
        return {
            "job_id":    job_id,
            "status":    "failed",
            "error":     job.get("error"),
            "elapsed_s": elapsed,
        }

    # queued hoặc processing
    return {
        "job_id":    job_id,
        "status":    job["status"],
        "elapsed_s": elapsed,
        "message":   "Đang xử lý, thử lại sau 5 giây.",
    }


# ══════════════════════════════════════════════════════════════════════════════
# GET /tryon/history — lịch sử ghép ảnh
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/history")
@limiter.limit("120/minute")
async def get_tryon_history(
    user_id: int = Query(..., gt=0),
    limit:   int = Query(default=20, le=100),
    offset:  int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Lấy lịch sử ghép ảnh của user, mới nhất trước."""
    repo    = TryonHistoryRepository(db)
    records = await repo.get_by_user_id(user_id, limit=limit, offset=offset)
    return {
        "user_id": user_id,
        "total":   len(records),
        "items": [
            {
                "id":               r.id,
                "garment_id":       r.garment_id,
                "result_image_url": r.result_image_url,
                "cloth_type":       r.cloth_type,
                "created_at":       r.created_at.isoformat(),
            }
            for r in records
        ],
    }
# ══════════════════════════════════════════════════════════════════════════════
# GET /tryon/history/admin — admin xem toàn bộ history
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/history/admin")
@limiter.limit("120/minute")
async def get_all_tryon_history(
    limit:  int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Admin — xem toàn bộ tryon history của tất cả users."""
    repo    = TryonHistoryRepository(db)
    records = await repo.get_all(limit=limit, offset=offset)
    total   = await repo.count_all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id":               r.id,
                "user_id":          r.user_id,
                "garment_id":       r.garment_id,
                "result_image_url": r.result_image_url,
                "cloth_type":       r.cloth_type,
                "created_at":       r.created_at.isoformat(),
            }
            for r in records
        ],
    }