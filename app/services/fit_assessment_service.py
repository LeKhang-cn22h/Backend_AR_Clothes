"""
fit_assessment_service.py
-------------------------
So sánh body measurements vs garment sizes → đánh giá fit theo ease allowance.

Ease (cm)              | tight     | good       | loose
-----------------------|-----------|------------|----------
chest                  | -2..2     | 2..8       | 8..∞
waist                  | -2..2     | 2..6       | 6..∞
hip                    | -2..2     | 2..8       | 8..∞
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException

from repositories.body_profile_repository import BodyProfileRepository
from repositories.garment_repository import GarmentRepository

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# RULES
# ══════════════════════════════════════════════════════════════════════════════

FIT_EASE = {
    "chest": {"tight": (-2, 2), "good": (2, 8),  "loose": (8, 999)},
    "waist": {"tight": (-2, 2), "good": (2, 6),  "loose": (6, 999)},
    "hip":   {"tight": (-2, 2), "good": (2, 8),  "loose": (8, 999)},
}

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]


def _classify(diff: float, region: str) -> str:
    """diff = garment_cm - body_cm; ease càng âm càng chật."""
    rules = FIT_EASE[region]
    if diff < rules["tight"][1]:
        return "tight"
    if diff < rules["good"][1]:
        return "good"
    return "loose"


def _aggregate_overall(statuses: list[str]) -> str:
    """Tổng hợp: nếu có tight → tight; nếu toàn loose → loose; còn lại → good."""
    if not statuses:
        return "unknown"
    if "tight" in statuses:
        return "tight"
    if all(s == "loose" for s in statuses):
        return "loose"
    return "good"


def _recommendation(overall: str) -> str:
    return {
        "tight":   "Hơi chật, có thể khó mặc — nên cân nhắc size lớn hơn",
        "good":    "Vừa vặn, có thể thoải mái mặc",
        "loose":   "Hơi rộng — bạn có thể chọn size nhỏ hơn nếu thích ôm",
        "unknown": "Không đủ dữ liệu để đánh giá",
    }[overall]


def _suggest_size(
    body: dict, sizes_spec: dict[str, dict]
) -> Optional[str]:
    """Chọn size có tổng diff trong vùng "good" nhiều nhất."""
    best: Optional[tuple[int, str]] = None
    for size, spec in sizes_spec.items():
        if not isinstance(spec, dict):
            continue
        good_count = 0
        for region in ("chest", "waist", "hip"):
            b = body.get(f"{region}_cm")
            g = spec.get(f"{region}_cm")
            if b is None or g is None:
                continue
            if _classify(g - b, region) == "good":
                good_count += 1
        rank = SIZE_ORDER.index(size.upper()) if size.upper() in SIZE_ORDER else 99
        candidate = (good_count, -rank, size)
        if best is None or candidate > best:
            best = candidate                          # type: ignore[assignment]
    return best[2] if best and best[0] > 0 else None  # type: ignore[index]


# ══════════════════════════════════════════════════════════════════════════════
# CORE COMPUTATION
# ══════════════════════════════════════════════════════════════════════════════

def assess_fit(
    body_measurements: dict,
    garment_sizes: dict,
) -> dict:
    """
    Args:
        body_measurements: {chest_cm, waist_cm, hip_cm, height_cm}
        garment_sizes:     {size_label, chest_cm, waist_cm, hip_cm, length_cm}

    Returns dict — xem docstring module.
    """
    out: dict = {}
    statuses: list[str] = []

    for region in ("chest", "waist", "hip"):
        body_v = body_measurements.get(f"{region}_cm")
        gar_v  = garment_sizes.get(f"{region}_cm")
        if body_v is None or gar_v is None:
            out[f"{region}_fit"] = {"diff_cm": None, "status": "unknown"}
            continue
        diff = round(float(gar_v) - float(body_v), 2)
        status = _classify(diff, region)
        statuses.append(status)
        out[f"{region}_fit"] = {"diff_cm": diff, "status": status}

    overall = _aggregate_overall(statuses)
    out["overall_fit"] = overall
    out["recommendation"] = _recommendation(overall)
    out["size_suggestion"] = None                       # set ngoài nếu có sizes_spec
    return out


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE (DB-aware)
# ══════════════════════════════════════════════════════════════════════════════

class FitAssessmentService:
    def __init__(
        self,
        body_profile_repo: BodyProfileRepository,
        garment_repo: GarmentRepository,
    ):
        self.body_profile_repo = body_profile_repo
        self.garment_repo = garment_repo

    @staticmethod
    def _profile_to_measurements(profile) -> dict:
        def f(v):
            return float(v) if v is not None else None
        return {
            "chest_cm":  f(profile.chest),
            "waist_cm":  f(profile.waist),
            "hip_cm":    f(profile.hip),
            "height_cm": f(profile.height),
        }

    @staticmethod
    def _garment_default_sizes(garment) -> dict:
        """Cố gắng lấy garment size spec từ các nguồn có thể có."""
        # Một vài bản model có column `sizes` JSON (xem photo_tryon_session_service).
        sizes = getattr(garment, "sizes", None)
        if isinstance(sizes, dict):
            return sizes
        return {}

    async def assess(
        self,
        body_profile_id: int,
        garment_id: int,
        size_label: Optional[str] = None,
    ) -> dict:
        """
        - Load body profile + garment từ DB.
        - Nếu garment có sizes spec (dict size→{chest,waist,hip,length}):
            • lấy size_label đã chọn (mặc định "M" nếu None) để đánh giá fit.
            • thêm size_suggestion = size có nhiều region "good" nhất.
        - Nếu không có sizes spec → fit_assessment trả unknown statuses.
        """
        profile = await self.body_profile_repo.get_by_id(body_profile_id)
        if not profile:
            raise HTTPException(
                status_code=404, detail="Khong tim thay body profile"
            )

        garment = await self.garment_repo.get_by_id(garment_id)
        if not garment:
            raise HTTPException(
                status_code=404, detail="Khong tim thay garment"
            )

        body = self._profile_to_measurements(profile)
        sizes_spec = self._garment_default_sizes(garment)

        # Pick size để chấm fit — ưu tiên size_label người dùng yêu cầu
        chosen_size = (size_label or "M").upper()
        size_data: dict = {}
        if sizes_spec:
            spec = sizes_spec.get(chosen_size) or sizes_spec.get(
                chosen_size.lower()
            )
            if isinstance(spec, dict):
                size_data = {
                    "size_label": chosen_size,
                    "chest_cm":  spec.get("chest_cm")  or spec.get("chest"),
                    "waist_cm":  spec.get("waist_cm")  or spec.get("waist"),
                    "hip_cm":    spec.get("hip_cm")    or spec.get("hip"),
                    "length_cm": spec.get("length_cm") or spec.get("length"),
                }

        result = assess_fit(body, size_data)
        if sizes_spec:
            result["size_suggestion"] = _suggest_size(body, sizes_spec)

        result["body_measurements"] = body
        result["garment_size"] = size_data or None
        result["selected_size"] = chosen_size if size_data else None
        return result
