"""
body_landmarks_service.py
-------------------------
Tính các điểm đo quan trọng trên SMPL-X mesh để dùng cho fit assessment.

Lấy vertex tại các index cố định (canonical SMPL-X topology) và quy về
khoảng cách / circumference dựa trên ellipse approximation.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# SMPL-X vertex indices — canonical, từ DECA & smpl-x documentation.
LANDMARK_VERTICES: dict[str, int] = {
    "left_shoulder":  3011,
    "right_shoulder": 6470,
    "left_hip":       3134,
    "right_hip":      6297,
    "neck":           3050,
    "bust_left":      3485,
    "bust_right":     6954,
    "waist_left":     3502,
    "waist_right":    6547,
}


# ══════════════════════════════════════════════════════════════════════════════
# CIRCUMFERENCE (cross-section ellipse)
# ══════════════════════════════════════════════════════════════════════════════

def _cross_section_circumference(
    vertices: np.ndarray,
    y_level: float,
    half_height: float = 0.015,
    trunk_thresh: float = 0.20,
) -> Optional[float]:
    """
    Lấy slice mỏng quanh y_level, ước tính chu vi bằng ellipse:
        C ≈ π * (w/2 + d/2) * 2 ≈ π * (w + d)/... — ta dùng công thức
        Ramanujan đơn giản: π*(w/2 + d/2) khớp với body_mesh_service.
    Trả về cm.
    """
    y = vertices[:, 1]
    zone = vertices[np.abs(y - y_level) < half_height]
    if len(zone) < 4:
        return None
    xc = float(np.median(zone[:, 0]))
    zone = zone[np.abs(zone[:, 0] - xc) < trunk_thresh]
    if len(zone) < 4:
        return None
    w = float(zone[:, 0].max() - zone[:, 0].min())
    d = float(zone[:, 2].max() - zone[:, 2].min())
    return float(np.pi * (w / 2 + d / 2) * 100)         # mét → cm


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def compute_landmarks(vertices: np.ndarray) -> dict:
    """
    Trích xuất landmark positions + đo các kích thước chính.

    Returns:
        {
            "landmarks":    {name: [x,y,z]} — vị trí (mét)
            "measurements": {
                "height_cm":         float,
                "shoulder_width_cm": float,
                "hip_width_cm":      float,
                "chest_circ_cm":     float,
                "waist_circ_cm":     float,
                "hip_circ_cm":       float,
            }
        }
    """
    vertices = np.asarray(vertices, dtype=np.float32)
    n_verts = vertices.shape[0]

    landmarks: dict[str, list[float]] = {}
    for name, idx in LANDMARK_VERTICES.items():
        if idx < n_verts:
            landmarks[name] = vertices[idx].tolist()
        else:
            logger.warning(f"Landmark vertex idx {idx} >= n_verts {n_verts}")

    # ── Linear distances ──────────────────────────────────────────────────
    def dist(a: str, b: str) -> Optional[float]:
        if a not in landmarks or b not in landmarks:
            return None
        pa = np.asarray(landmarks[a]); pb = np.asarray(landmarks[b])
        return float(np.linalg.norm(pa - pb) * 100)     # mét → cm

    shoulder_width = dist("left_shoulder", "right_shoulder")
    hip_width      = dist("left_hip", "right_hip")

    # ── Circumferences (cross-section ellipse) ────────────────────────────
    y = vertices[:, 1]
    y_min = float(y.min()); y_max = float(y.max())
    y_range = y_max - y_min
    height_cm = float(y_range * 100)

    chest_y = y_min + 0.73 * y_range                    # chest ~ 73%
    waist_y = y_min + 0.63 * y_range                    # waist ~ 63%
    hip_y   = y_min + 0.47 * y_range                    # hip   ~ 47%

    chest_circ = _cross_section_circumference(vertices, chest_y, trunk_thresh=0.17)
    waist_circ = _cross_section_circumference(vertices, waist_y, trunk_thresh=0.20)
    hip_circ   = _cross_section_circumference(vertices, hip_y,   trunk_thresh=0.20)

    measurements = {
        "height_cm":         height_cm,
        "shoulder_width_cm": shoulder_width,
        "hip_width_cm":      hip_width,
        "chest_circ_cm":     chest_circ,
        "waist_circ_cm":     waist_circ,
        "hip_circ_cm":       hip_circ,
    }

    return {"landmarks": landmarks, "measurements": measurements}


def compute_landmarks_from_beta(beta: list[float], gender: str) -> dict:
    """Tiện cho router: từ beta + gender → forward SMPL-X → compute_landmarks."""
    import os
    import smplx
    import torch

    smplx_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "ml_models", "models"
    )
    model = smplx.create(
        smplx_dir, model_type="smplx", gender=gender,
        num_betas=10, num_expression_coeffs=10, ext="npz",
    )
    with torch.no_grad():
        out = model(
            betas=torch.tensor(beta, dtype=torch.float32).unsqueeze(0),
            return_verts=True,
        )
    return compute_landmarks(out.vertices[0].numpy())
