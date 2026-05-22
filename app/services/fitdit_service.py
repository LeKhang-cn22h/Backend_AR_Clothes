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

# Set URL này sau khi Colab Cell 7 chạy xong
# Có thể override bằng env var: FITDIT_COLAB_URL=https://xxxx.ngrok-free.app
FITDIT_COLAB_URL: str = os.getenv(
    "FITDIT_COLAB_URL",
    "https://YOUR_NGROK_URL_HERE.ngrok-free.app",  # ← paste URL từ Colab vào đây
)

# Timeout cho inference (FitDiT trên T4 ~30-60s per request)
REQUEST_TIMEOUT_S: int = int(os.getenv("FITDIT_TIMEOUT", "120"))

# Retry config
MAX_RETRIES: int = 2
RETRY_DELAY_S: float = 2.0


# ── Internal Helpers ──────────────────────────────────────────────────────────

def _pil_to_base64(img: Image.Image, fmt: str = "PNG") -> str:
    """PIL Image → base64 string."""
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _base64_to_pil(b64_str: str) -> Image.Image:
    """base64 string → PIL Image."""
    img_bytes = base64.b64decode(b64_str)
    return Image.open(io.BytesIO(img_bytes)).convert("RGB")


def _load_image(path_or_pil) -> Image.Image:
    """Nhận path (str/Path) hoặc PIL Image, luôn trả về PIL Image."""
    if isinstance(path_or_pil, Image.Image):
        return path_or_pil.convert("RGB")
    return Image.open(path_or_pil).convert("RGB")


def _get_base_url() -> str:
    """Trả về base URL, strip trailing slash."""
    return FITDIT_COLAB_URL.rstrip("/")


def _make_client() -> httpx.Client:
    """Tạo httpx client với timeout phù hợp."""
    return httpx.Client(
        timeout=httpx.Timeout(
            connect=10.0,
            read=REQUEST_TIMEOUT_S,
            write=30.0,
            pool=5.0,
        ),
        follow_redirects=True,
    )


# ── Public Interface ──────────────────────────────────────────────────────────

def is_available() -> bool:
    """
    Kiểm tra FitDiT Colab server còn sống không.
    Gọi trước khi try_on để handle gracefully.
    """
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
    """
    Lấy thông tin chi tiết về Colab server.
    Returns dict với keys: available, url, vram_used_gb, uptime_s, error
    """
    try:
        with _make_client() as client:
            r = client.get(f"{_get_base_url()}/health", timeout=10)
            if r.status_code == 200:
                data = r.json()
                return {
                    "available": True,
                    "url": _get_base_url(),
                    **data,
                }
    except Exception as e:
        return {
            "available": False,
            "url": _get_base_url(),
            "error": str(e),
        }
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
    """
    Virtual try-on qua FitDiT Colab server.

    Args:
        person_image_path: Path đến ảnh người (str, Path, hoặc PIL.Image)
        garment_image_path: Path đến ảnh quần áo (str, Path, hoặc PIL.Image)
        category: "upper" | "lower" | "full"
        num_steps: Inference steps (ít hơn = nhanh hơn, chất lượng thấp hơn)
        guidance_scale: CFG scale
        seed: Optional seed để reproducibility
        request_id: Optional ID để track trong logs

    Returns:
        PIL.Image kết quả

    Raises:
        RuntimeError: Nếu server không available hoặc inference fail
    """
    person_img = _load_image(person_image_path)
    garment_img = _load_image(garment_image_path)
    return try_on_from_pil(
        person_img=person_img,
        garment_img=garment_img,
        category=category,
        num_steps=num_steps,
        guidance_scale=guidance_scale,
        seed=seed,
        request_id=request_id,
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
    """
    Như try_on() nhưng nhận PIL Images trực tiếp.
    Đây là hàm core — try_on() wrap hàm này.
    """
    req_id = request_id or str(uuid.uuid4())[:8]
    base_url = _get_base_url()

    payload = {
        "person_image": _pil_to_base64(person_img),
        "garment_image": _pil_to_base64(garment_img),
        "category": category,
        "num_steps": num_steps,
        "guidance_scale": guidance_scale,
        "seed": seed,
        "request_id": req_id,
    }

    last_error: Exception = RuntimeError("No attempts made")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                f"[{req_id}] FitDiT try-on request "
                f"(attempt {attempt}/{MAX_RETRIES}) "
                f"category={category} steps={num_steps}"
            )
            t0 = time.time()

            with _make_client() as client:
                response = client.post(
                    f"{base_url}/try-on",
                    json=payload,
                )

            elapsed = time.time() - t0

            if response.status_code == 200:
                data = response.json()
                result_img = _base64_to_pil(data["result_image"])
                logger.info(
                    f"[{req_id}] Try-on success in {elapsed:.1f}s "
                    f"(server reported {data.get('inference_time_s', '?')}s)"
                )
                return result_img

            # HTTP error từ server
            error_detail = response.text[:200]
            logger.error(
                f"[{req_id}] Server error {response.status_code}: {error_detail}"
            )
            last_error = RuntimeError(
                f"FitDiT server returned {response.status_code}: {error_detail}"
            )

        except httpx.TimeoutException as e:
            logger.warning(f"[{req_id}] Timeout on attempt {attempt}: {e}")
            last_error = RuntimeError(
                f"FitDiT request timed out after {REQUEST_TIMEOUT_S}s. "
                "Try reducing num_steps or check Colab server."
            )
        except httpx.ConnectError as e:
            logger.warning(f"[{req_id}] Connection error on attempt {attempt}: {e}")
            last_error = RuntimeError(
                f"Cannot connect to FitDiT server at {base_url}. "
                "Check ngrok URL and Colab session."
            )
        except Exception as e:
            logger.error(f"[{req_id}] Unexpected error: {e}", exc_info=True)
            last_error = e

        # Retry delay (không delay ở attempt cuối)
        if attempt < MAX_RETRIES:
            logger.info(f"[{req_id}] Retrying in {RETRY_DELAY_S}s...")
            time.sleep(RETRY_DELAY_S)

    raise RuntimeError(f"FitDiT try-on failed after {MAX_RETRIES} attempts: {last_error}") from last_error


# ── Async variants (nếu endpoint FastAPI local dùng async) ────────────────────

async def try_on_async(
    person_image_path,
    garment_image_path,
    category: str = "upper",
    num_steps: int = 20,
    guidance_scale: float = 2.0,
    seed: Optional[int] = None,
    request_id: Optional[str] = None,
) -> Image.Image:
    """Async version của try_on() dùng httpx.AsyncClient."""
    import asyncio

    person_img = _load_image(person_image_path)
    garment_img = _load_image(garment_image_path)
    return await try_on_from_pil_async(
        person_img=person_img,
        garment_img=garment_img,
        category=category,
        num_steps=num_steps,
        guidance_scale=guidance_scale,
        seed=seed,
        request_id=request_id,
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
    """Async version của try_on_from_pil()."""
    req_id = request_id or str(uuid.uuid4())[:8]
    base_url = _get_base_url()

    payload = {
        "person_image": _pil_to_base64(person_img),
        "garment_image": _pil_to_base64(garment_img),
        "category": category,
        "num_steps": num_steps,
        "guidance_scale": guidance_scale,
        "seed": seed,
        "request_id": req_id,
    }

    timeout = httpx.Timeout(connect=10.0, read=REQUEST_TIMEOUT_S, write=30.0, pool=5.0)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"[{req_id}] Async try-on attempt {attempt}/{MAX_RETRIES}")
                response = await client.post(f"{base_url}/try-on", json=payload)

                if response.status_code == 200:
                    data = response.json()
                    return _base64_to_pil(data["result_image"])

                raise RuntimeError(f"Server {response.status_code}: {response.text[:200]}")

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt == MAX_RETRIES:
                    raise RuntimeError(f"FitDiT async failed: {e}") from e
                import asyncio
                await asyncio.sleep(RETRY_DELAY_S)

    raise RuntimeError("FitDiT async try-on failed")


# ── CLI Quick Test ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Test nhanh từ command line:
        python fitdit_service.py
    
    Hoặc với ảnh thực:
        python fitdit_service.py person.jpg garment.jpg output.png
    """
    import sys

    logging.basicConfig(level=logging.INFO)

    print(f"FitDiT Service — target: {_get_base_url()}")
    print(f"Checking availability...", end=" ", flush=True)

    if not is_available():
        print(" Server not available")
        print("   → Check FITDIT_COLAB_URL env var hoặc cập nhật trong file")
        sys.exit(1)

    status = get_status()
    print("")
    print(f"   VRAM: {status.get('vram_used_gb', '?')} GB used")
    print(f"   Uptime: {status.get('uptime_s', '?')}s")

    if len(sys.argv) == 4:
        person_path, garment_path, output_path = sys.argv[1], sys.argv[2], sys.argv[3]
        print(f"\nRunning try-on: {person_path} + {garment_path} → {output_path}")
        result = try_on(person_path, garment_path)
        result.save(output_path)
        print(f" Saved to {output_path}")
    else:
        print("\n Service is ready!")
        print("   Usage: python fitdit_service.py person.jpg garment.jpg output.png")