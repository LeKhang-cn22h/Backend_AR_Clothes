from __future__ import annotations

import base64
import io
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx
from PIL import Image

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

REQUEST_TIMEOUT_S: int = int(os.getenv("FITDIT_TIMEOUT", "3600"))
MAX_RETRIES: int = 2
RETRY_DELAY_S: float = 2.0


# ── Internal Helpers ──────────────────────────────────────────────────────────

def _pil_to_base64(img: Image.Image, fmt: str = "PNG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _base64_to_pil(b64_str: str) -> Image.Image:
    img_bytes = base64.b64decode(b64_str)
    return Image.open(io.BytesIO(img_bytes)).convert("RGB")


def _load_image(path_or_pil) -> Image.Image:
    if isinstance(path_or_pil, Image.Image):
        return path_or_pil.convert("RGB")
    return Image.open(path_or_pil).convert("RGB")


def _get_base_url() -> str:
    try:
        from config import settings
        if settings.FITDIT_COLAB_URL:
            return settings.FITDIT_COLAB_URL.rstrip("/")
    except Exception:
        pass
    return os.getenv("FITDIT_COLAB_URL", "").rstrip("/")


def _make_client() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(connect=10.0, read=REQUEST_TIMEOUT_S, write=30.0, pool=5.0),
        follow_redirects=True,
    )


# ── Public Interface ──────────────────────────────────────────────────────────

def is_available() -> bool:
    try:
        with _make_client() as client:
            r = client.get(f"{_get_base_url()}/health", timeout=10)
            if r.status_code == 200:
                data = r.json()
                return data.get("status") == "ok" and data.get("model_loaded", False)
    except Exception as e:
        logger.warning(f"FitDiT health check failed: {e}")
    return False


def get_status() -> dict:
    try:
        with _make_client() as client:
            r = client.get(f"{_get_base_url()}/health", timeout=10)
            if r.status_code == 200:
                data = r.json()
                return {"available": True, "url": _get_base_url(), **data}
    except Exception as e:
        return {"available": False, "url": _get_base_url(), "error": str(e)}
    return {"available": False, "url": _get_base_url()}


def try_on(
    person_image_path,
    garment_image_path,
    category: str = "upper",
    num_steps: int = 20,
    guidance_scale: float = 2.0,
    seed: Optional[int] = None,
    request_id: Optional[str] = None,
) -> Image.Image:
    person_img  = _load_image(person_image_path)
    garment_img = _load_image(garment_image_path)
    return try_on_from_pil(
        person_img=person_img, garment_img=garment_img,
        category=category, num_steps=num_steps,
        guidance_scale=guidance_scale, seed=seed, request_id=request_id,
    )


def try_on_from_pil(
    person_img: Image.Image,
    garment_img: Image.Image,
    category: str = "upper",
    num_steps: int = 20,
    guidance_scale: float = 2.0,
    seed: Optional[int] = None,
    request_id: Optional[str] = None,
) -> Image.Image:
    """Sync version — gọi /try-on trực tiếp (dùng cho CLI test)."""
    req_id   = request_id or str(uuid.uuid4())[:8]
    base_url = _get_base_url()
    payload  = {
        "person_image":   _pil_to_base64(person_img),
        "garment_image":  _pil_to_base64(garment_img),
        "category":       category,
        "num_steps":      num_steps,
        "guidance_scale": guidance_scale,
        "seed":           seed,
        "request_id":     req_id,
    }
    last_error: Exception = RuntimeError("No attempts made")
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"[{req_id}] try-on attempt {attempt}/{MAX_RETRIES}")
            t0 = time.time()
            with _make_client() as client:
                response = client.post(f"{base_url}/try-on", json=payload)
            elapsed = time.time() - t0
            if response.status_code == 200:
                data = response.json()
                logger.info(f"[{req_id}] Success in {elapsed:.1f}s")
                return _base64_to_pil(data["result_image"])
            last_error = RuntimeError(f"Server {response.status_code}: {response.text[:200]}")
        except httpx.TimeoutException as e:
            last_error = RuntimeError(f"Timeout after {REQUEST_TIMEOUT_S}s")
        except httpx.ConnectError as e:
            last_error = RuntimeError(f"Cannot connect to {base_url}")
        except Exception as e:
            last_error = e
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY_S)
    raise RuntimeError(f"try-on failed after {MAX_RETRIES} attempts: {last_error}")


async def try_on_async(
    person_image_path,
    garment_image_path,
    category: str = "upper",
    num_steps: int = 20,
    guidance_scale: float = 2.0,
    seed: Optional[int] = None,
    request_id: Optional[str] = None,
) -> Image.Image:
    person_img  = _load_image(person_image_path)
    garment_img = _load_image(garment_image_path)
    return await try_on_from_pil_async(
        person_img=person_img, garment_img=garment_img,
        category=category, num_steps=num_steps,
        guidance_scale=guidance_scale, seed=seed, request_id=request_id,
    )


async def try_on_from_pil_async(
    person_img: Image.Image,
    garment_img: Image.Image,
    category: str = "upper",
    num_steps: int = 20,
    guidance_scale: float = 2.0,
    seed: Optional[int] = None,
    request_id: Optional[str] = None,
) -> Image.Image:
    """
    Async version — dùng /submit + poll /status.
    Không bị timeout ngrok dù inference mất hàng chục phút.
    """
    import asyncio

    req_id   = request_id or str(uuid.uuid4())[:8]
    base_url = _get_base_url()
    payload  = {
        "person_image":   _pil_to_base64(person_img),
        "garment_image":  _pil_to_base64(garment_img),
        "category":       category,
        "num_steps":      num_steps,
        "guidance_scale": guidance_scale,
        "seed":           seed,
        "request_id":     req_id,
        "resolution":     "768x1024",
    }

    # ── Bước 1: Submit job — response về ngay trong 1s ────────────────────────
    submit_timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=5.0)
    async with httpx.AsyncClient(timeout=submit_timeout, follow_redirects=True) as client:
        try:
            resp = await client.post(f"{base_url}/submit", json=payload)
        except Exception as e:
            raise RuntimeError(f"Không kết nối được FitDiT server: {e}")
        if resp.status_code != 200:
            raise RuntimeError(f"FitDiT /submit lỗi {resp.status_code}: {resp.text[:200]}")
        job_id = resp.json()["job_id"]
        logger.info(f"[{req_id}] Submitted FitDiT job {job_id[:8]}")

    # ── Bước 2: Poll /status mỗi 5s ──────────────────────────────────────────
    poll_timeout  = httpx.Timeout(connect=10.0, read=15.0, write=10.0, pool=5.0)
    max_wait_s    = REQUEST_TIMEOUT_S
    poll_interval = 5.0
    waited        = 0.0

    while waited < max_wait_s:
        await asyncio.sleep(poll_interval)
        waited += poll_interval
        try:
            async with httpx.AsyncClient(timeout=poll_timeout, follow_redirects=True) as client:
                resp = await client.get(f"{base_url}/status/{job_id}")
        except Exception as e:
            logger.warning(f"[{req_id}] Poll error (retry): {e}")
            continue
        if resp.status_code != 200:
            logger.warning(f"[{req_id}] Poll {resp.status_code}, retry...")
            continue
        data   = resp.json()
        status = data.get("status")
        logger.info(f"[{req_id}] Poll → {status} ({waited:.0f}s)")
        if status == "done":
            return _base64_to_pil(data["result_image"])
        if status == "failed":
            raise RuntimeError(f"FitDiT inference thất bại: {data.get('error')}")
        # queued | processing → tiếp tục chờ

    raise RuntimeError(f"FitDiT job timeout sau {max_wait_s}s")


# ── CLI Quick Test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    print(f"FitDiT Service — target: {_get_base_url()}")
    if not is_available():
        print("Server not available")
        sys.exit(1)
    status = get_status()
    print(f"VRAM: {status.get('vram_used_gb', '?')} GB | Uptime: {status.get('uptime_s', '?')}s")
    if len(sys.argv) == 4:
        result = try_on(sys.argv[1], sys.argv[2])
        result.save(sys.argv[3])
        print(f"Saved to {sys.argv[3]}")