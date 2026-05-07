"""
body_mesh_service.py
--------------------
SMPL-X + ellipse optimization + anthropometric corrections.

Corrections từ calibration 20 body types:
  female: height=-0.5, chest=-3.5, waist=-5.0, hip=-3.0
  male:   height=-4.0, chest=+4.0, waist=-5.1, hip=-1.5
"""

import hashlib
import logging
import os
import tempfile
from dataclasses import dataclass
from typing import Optional

import cloudinary.uploader
import numpy as np
import smplx
import torch
import torch.nn as nn
import trimesh

logger = logging.getLogger(__name__)

SMPLX_MODEL_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "ml_models", "models"
)

EARLY_STOP_THRESHOLD = 0.008
MAX_ITER_LBFGS = 40
MAX_ITER_ADAM  = 100

SMPLX_CORRECTIONS = {
    "female":  {"height": -0.5, "chest": -3.5, "waist": -5.0, "hip": -3.0},
    "male":    {"height": -4.0, "chest":  4.0, "waist": -5.1, "hip": -1.5},
    "neutral": {"height": -2.1, "chest": -0.2, "waist": -5.1, "hip": -2.4},
}


@dataclass
class BodyMeshResult:
    """
    Kết quả trả về sau optimization.

    glb_url:             URL Cloudinary — Babylon.js load URL này
    beta:                10 số — shape parameters tìm được
    beta_hash:           16 ký tự — key cache trong DB
    iterations:          Số vòng thực tế đã chạy
    from_cache:          True nếu lấy từ cache
    corrected_measures:  Số đo đã apply correction — dùng cho fit assessment
    raw_measures:        Số đo thô từ mesh — dùng để debug
    """
    glb_url: str
    beta: list[float]
    beta_hash: str
    iterations: int
    from_cache: bool
    corrected_measures: dict[str, float]
    raw_measures: dict[str, float]


# ══════════════════════════════════════════════════════════════════════════════
# BETA HASH
# ══════════════════════════════════════════════════════════════════════════════

def compute_beta_hash(
    height: float, chest: float, waist: float, hip: float,
    shoulder: float, arm_length: float, inseam: float, gender: str,
) -> str:
    """Hash 16 ký tự từ số đo, làm tròn 0.5cm để tránh cache miss."""
    def snap(v: float) -> float:
        return round(v * 2) / 2

    key = (
        f"{snap(height)}_{snap(chest)}_{snap(waist)}_{snap(hip)}_"
        f"{snap(shoulder)}_{snap(arm_length)}_{snap(inseam)}_{gender}"
    )
    return hashlib.md5(key.encode()).hexdigest()[:16]


# ══════════════════════════════════════════════════════════════════════════════
# CORRECTION
# ══════════════════════════════════════════════════════════════════════════════

def apply_corrections(raw: dict[str, float], gender: str) -> dict[str, float]:
    """
    Áp dụng correction factors vào số đo thô từ mesh.

    SMPL-X T-pose có systematic bias:
    - Eo rộng hơn ~5cm do thân bị kéo giãn
    - Nam: chiều cao cao hơn ~4cm
    Correction học từ calibration 20 body types.
    """
    corr = SMPLX_CORRECTIONS.get(gender, SMPLX_CORRECTIONS["neutral"])
    return {
        "height": raw["height"] + corr["height"],
        "chest":  raw["chest"]  + corr["chest"],
        "waist":  raw["waist"]  + corr["waist"],
        "hip":    raw["hip"]    + corr["hip"],
    }


# ══════════════════════════════════════════════════════════════════════════════
# ĐO SỐ ĐO TỪ MESH
# ══════════════════════════════════════════════════════════════════════════════

def measure_from_mesh(vertices: np.ndarray, gender: str) -> tuple[dict, dict]:
    """
    Đo số đo từ mesh numpy.
    Returns: (raw_measures, corrected_measures) — đơn vị cm
    """
    y       = vertices[:, 1]
    y_min   = y.min()
    y_range = y.max() - y_min

    def circ(pcts, arm_thresh=None, trunk_thresh=0.20):
        results = []
        for p in pcts:
            yc   = y_min + p * y_range
            zone = vertices[np.abs(y - yc) < 0.015 * y_range]
            if arm_thresh:
                zone = zone[np.abs(zone[:, 0]) < arm_thresh]
            elif trunk_thresh:
                xc   = np.median(zone[:, 0]) if len(zone) > 0 else 0
                zone = zone[np.abs(zone[:, 0] - xc) < trunk_thresh]
            if len(zone) < 4:
                continue
            w = zone[:, 0].max() - zone[:, 0].min()
            d = zone[:, 2].max() - zone[:, 2].min()
            results.append(np.pi * (w/2 + d/2) * 100)
        return results

    raw = {
        "height": float((y.max() - y.min()) * 100),
        "chest":  max(circ([0.71,0.73,0.75], arm_thresh=0.17) or [0]),
        "waist":  min(circ([0.61,0.62,0.63,0.64,0.65,0.66],
                           trunk_thresh=0.20) or [999]),
        "hip":    max(circ([0.45,0.47,0.49], trunk_thresh=0.20) or [0]),
    }
    return raw, apply_corrections(raw, gender)


# ══════════════════════════════════════════════════════════════════════════════
# OPTIMIZATION
# ══════════════════════════════════════════════════════════════════════════════

def _soft_circ(v, y, ym, yr, pcts, PI, arm_thresh=None, trunk_mask=False):
    """Soft circumference differentiable dùng trong optimization loop."""
    results = []
    sharp   = 200.0
    for p in pcts:
        yc   = ym + p * yr
        hw   = 0.015 * yr
        mask = (torch.sigmoid(sharp*(y-(yc-hw))) *
                torch.sigmoid(sharp*((yc+hw)-y)))
        if arm_thresh:
            mask = mask * torch.sigmoid(sharp*(arm_thresh-v[:,0].abs()))
        elif trunk_mask:
            xc   = (v[:,0]*mask).sum()/(mask.sum()+1e-6)
            mask = mask * torch.sigmoid(sharp*(0.20-(v[:,0]-xc).abs()))
        w = (v[:,0]*mask).max()-(v[:,0]*mask).min()
        d = (v[:,2]*mask).max()-(v[:,2]*mask).min()
        results.append(PI*(w/2+d/2))
    return results


def _compute_loss(beta, smplx_model, targets, weights):
    """Tính loss từ beta hiện tại."""
    PI  = torch.tensor(np.pi, dtype=torch.float32, device=beta.device)
    out = smplx_model(betas=beta.unsqueeze(0), return_verts=True)
    v   = out.vertices[0]
    y   = v[:,1]; ym = y.min(); yr = y.max()-ym

    h   = yr
    c   = torch.stack(_soft_circ(v,y,ym,yr,
            [0.71,0.73,0.75],PI,arm_thresh=0.17)).max()
    w   = torch.stack(_soft_circ(v,y,ym,yr,
            [0.61,0.62,0.63,0.64,0.65,0.66],PI,
            trunk_mask=True)).min()
    hip = torch.stack(_soft_circ(v,y,ym,yr,
            [0.45,0.47,0.49],PI,trunk_mask=True)).max()

    cur  = torch.stack([h, c, w, hip])
    loss = (weights*(cur-targets)**2).sum() + 0.01*(beta**2).sum()
    return loss, cur


def run_optimization(
    target_height_m: float,
    target_chest_m: float,
    target_waist_m: float,
    target_hip_m: float,
    gender: str,
    warm_start_beta: Optional[list[float]] = None,
) -> tuple[torch.Tensor, int]:
    """
    Tìm beta sao cho mesh SMPL-X có số đo khớp target.

    Optimization nhắm thẳng vào target thô từ user.
    Correction chỉ apply SAU KHI đo xong — không trộn lẫn.

    Giai đoạn 1: L-BFGS — hội tụ nhanh từ điểm khởi tạo
    Giai đoạn 2: Adam   — tinh chỉnh, dừng sớm khi đủ chính xác
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Optimization chạy trên: {device}")

    smplx_model = smplx.create(
        SMPLX_MODEL_DIR, model_type="smplx", gender=gender,
        num_betas=10, num_expression_coeffs=10, ext="npz",
    ).to(device)

    if warm_start_beta is not None:
        init = torch.tensor(warm_start_beta, dtype=torch.float32, device=device)
        logger.info("Warm start")
    else:
        init = torch.zeros(10, dtype=torch.float32, device=device)
        logger.info("Cold start")

    beta    = nn.Parameter(init.clone())

    # Target thẳng từ user — KHÔNG adjust correction ở đây
    targets = torch.tensor(
        [target_height_m, target_chest_m, target_waist_m, target_hip_m],
        dtype=torch.float32, device=device
    )
    weights = torch.tensor(
        [2.0, 1.0, 4.0, 1.0],
        dtype=torch.float32, device=device
    )

    total_iters = 0
    error       = float("inf")

    # Giai đoạn 1: L-BFGS
    lbfgs = torch.optim.LBFGS([beta], lr=1.0, max_iter=20,
                                line_search_fn="strong_wolfe")
    for i in range(MAX_ITER_LBFGS):
        def closure():
            lbfgs.zero_grad()
            loss, _ = _compute_loss(beta, smplx_model, targets, weights)
            loss.backward()
            return loss
        lbfgs.step(closure)
        total_iters += 1

        with torch.no_grad():
            _, cur = _compute_loss(beta, smplx_model, targets, weights)
            error  = (cur.detach()-targets).abs().sum().item()
        if error < EARLY_STOP_THRESHOLD:
            logger.info(f"L-BFGS early stop iter {i+1}, error={error:.4f}m")
            return beta.detach().cpu(), total_iters

    # Giai đoạn 2: Adam
    adam = torch.optim.Adam([beta], lr=0.01)
    for i in range(MAX_ITER_ADAM):
        adam.zero_grad()
        loss, cur = _compute_loss(beta, smplx_model, targets, weights)
        loss.backward()
        adam.step()
        total_iters += 1

        error = (cur.detach()-targets).abs().sum().item()
        if error < EARLY_STOP_THRESHOLD:
            logger.info(f"Adam early stop iter {i+1}, error={error:.4f}m")
            break

    logger.info(f"Optimization xong sau {total_iters} iterations")
    return beta.detach().cpu(), total_iters


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT GLB
# ══════════════════════════════════════════════════════════════════════════════

def export_to_glb(beta: torch.Tensor, gender: str) -> str:
    """Sinh mesh từ beta → export file GLB tạm."""
    smplx_model = smplx.create(
        SMPLX_MODEL_DIR, model_type="smplx", gender=gender,
        num_betas=10, num_expression_coeffs=10, ext="npz",
    )
    with torch.no_grad():
        output = smplx_model(betas=beta.unsqueeze(0), return_verts=True)

    vertices = output.vertices[0].numpy()
    faces    = smplx_model.faces
    mesh     = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)

    tmp = tempfile.NamedTemporaryFile(suffix=".glb", delete=False)
    tmp.close()
    mesh.export(tmp.name)
    return tmp.name


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE CHÍNH
# ══════════════════════════════════════════════════════════════════════════════

async def generate_body_mesh(
    height: float, chest: float, waist: float, hip: float,
    shoulder: float, arm_length: float, inseam: float, gender: str,
    cached_beta: Optional[list[float]] = None,
    warm_start_beta: Optional[list[float]] = None,
) -> BodyMeshResult:
    """
    Hàm public được gọi từ photo_avatar_service.
    Số đo đầu vào đơn vị CM.
    Trả về corrected_measures để dùng cho fit assessment.
    """
    beta_hash = compute_beta_hash(
        height, chest, waist, hip, shoulder, arm_length, inseam, gender
    )

    smplx_model = smplx.create(
        SMPLX_MODEL_DIR, model_type="smplx", gender=gender,
        num_betas=10, num_expression_coeffs=10, ext="npz",
    )

    def get_measures(b: torch.Tensor) -> tuple[dict, dict]:
        with torch.no_grad():
            out = smplx_model(betas=b.unsqueeze(0), return_verts=True)
        return measure_from_mesh(out.vertices[0].numpy(), gender)

    if cached_beta is not None:
        logger.info(f"Cache hit: beta_hash={beta_hash}")
        beta_tensor    = torch.tensor(cached_beta, dtype=torch.float32)
        raw, corrected = get_measures(beta_tensor)
        glb_path       = export_to_glb(beta_tensor, gender)
        glb_url        = _upload_to_cloudinary(glb_path, beta_hash)
        return BodyMeshResult(
            glb_url=glb_url, beta=cached_beta,
            beta_hash=beta_hash, iterations=0, from_cache=True,
            corrected_measures=corrected, raw_measures=raw,
        )

    beta_tensor, iters = run_optimization(
        target_height_m=height / 100,
        target_chest_m=chest   / 100,
        target_waist_m=waist   / 100,
        target_hip_m=hip       / 100,
        gender=gender,
        warm_start_beta=warm_start_beta,
    )

    raw, corrected = get_measures(beta_tensor)
    glb_path       = export_to_glb(beta_tensor, gender)
    glb_url        = _upload_to_cloudinary(glb_path, beta_hash)

    return BodyMeshResult(
        glb_url=glb_url, beta=beta_tensor.tolist(),
        beta_hash=beta_hash, iterations=iters, from_cache=False,
        corrected_measures=corrected, raw_measures=raw,
    )


def _upload_to_cloudinary(glb_path: str, beta_hash: str) -> str:
    """Upload GLB lên Cloudinary, xóa file tạm sau khi xong."""
    try:
        result = cloudinary.uploader.upload(
            glb_path, resource_type="raw",
            folder="body_meshes",
            public_id=f"body_{beta_hash}",
            overwrite=True,
        )
        return result["secure_url"]
    finally:
        if os.path.exists(glb_path):
            os.unlink(glb_path)