"""
Gợi ý size quần áo dựa trên thông tin cơ thể.
Hỗ trợ 2 chế độ input:
    • BASIC   — height + weight → tra bảng khuyến nghị của chính garment đó
    • DETAIL  — chest/waist/hip → tính ease allowance so với số đo quần áo

Ease allowance (garment_cm - body_cm):
    Region  | very_tight | tight   | good   | loose   | very_loose
    --------|------------|---------|--------|---------|------------
    chest   |   < -2     | -2..2   | 2..8   | 8..12   |   > 12
    waist   |   < -2     | -2..2   | 2..6   | 6..12   |   > 12
    hip     |   < -2     | -2..2   | 2..8   | 8..12   |   > 12
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException

from repositories.body_profile_repository import BodyProfileRepository
from repositories.garment_size_spec_repository import GarmentSizeSpecRepository

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]

FIT_EASE: dict[str, dict[str, tuple[float, float]]] = {
    "chest": {
        "very_tight": (-999, -2),
        "tight":      (-2,    2),
        "good":       (2,     8),
        "loose":      (8,    12),
        "very_loose": (12,  999),
    },
    "waist": {
        "very_tight": (-999, -2),
        "tight":      (-2,    2),
        "good":       (2,     6),
        "loose":      (6,    12),
        "very_loose": (12,  999),
    },
    "hip": {
        "very_tight": (-999, -2),
        "tight":      (-2,    2),
        "good":       (2,     8),
        "loose":      (8,    12),
        "very_loose": (12,  999),
    },
}

RECOMMENDATIONS: dict[str, str] = {
    "very_tight": "Rất chật — nên chọn size lớn hơn ít nhất 1 bậc",
    "tight":      "Hơi chật — có thể khó mặc, nên cân nhắc size lớn hơn",
    "good":       "Vừa vặn — bạn có thể mặc thoải mái",
    "loose":      "Hơi rộng — có thể chọn size nhỏ hơn nếu thích ôm",
    "very_loose": "Quá rộng — nên chọn size nhỏ hơn ít nhất 1 bậc",
    "unknown":    "Không đủ dữ liệu để đánh giá",
}


# ══════════════════════════════════════════════════════════════════════════════
# PRIVATE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _sorted_sizes(size_labels: list[str]) -> list[str]:
    return sorted(
        [s.upper() for s in size_labels],
        key=lambda x: SIZE_ORDER.index(x) if x in SIZE_ORDER else 99,
    )


def _classify_ease(diff: float, region: str) -> str:
    """diff = garment_cm - body_cm. Âm → chật, dương lớn → rộng."""
    for label, (lo, hi) in FIT_EASE[region].items():
        if lo <= diff < hi:
            return label
    return "very_loose"


def _aggregate_overall(statuses: list[str]) -> str:
    """Worst-case: ưu tiên cảnh báo chật trước, rộng sau."""
    if not statuses:
        return "unknown"
    for p in ["very_tight", "tight", "very_loose", "loose", "good"]:
        if p in statuses:
            return p
    return "good"


def _suggest_size_from_specs(body: dict, specs: list[dict]) -> Optional[str]:
    """
    Chọn size tốt nhất dựa trên ease (DETAIL mode).
    Tiêu chí: nhiều region 'good' nhất → nếu bằng nhau thì ưu tiên size nhỏ hơn.
    """
    best: Optional[tuple] = None  # (good_count, -size_rank, size_label)

    for spec in specs:
        size_label = (spec.get("size_label") or "").upper()
        good_count = 0
        for region in ("chest", "waist", "hip"):
            b = body.get(f"{region}_cm")
            g = spec.get(f"{region}_cm")
            if b is None or g is None:
                continue
            if _classify_ease(float(g) - float(b), region) == "good":
                good_count += 1

        rank = SIZE_ORDER.index(size_label) if size_label in SIZE_ORDER else 99
        candidate = (good_count, -rank, size_label)
        if best is None or candidate > best:
            best = candidate

    return best[2] if best and best[0] > 0 else None


def _basic_size_lookup(
    height_cm: float,
    weight_kg: float,
    specs: list[dict],
) -> Optional[str]:
    """
    Tra size theo height/weight từ bảng khuyến nghị của chính garment.

    Mỗi spec có thể có height_min/max và weight_min/max do shop nhập.
    - Nếu cả 2 đều match → trả size đó.
    - Nếu spec không có height range → chỉ xét weight (và ngược lại).
    - Nếu không match chính xác → tìm spec gần nhất theo weight.
    """
    # Pass 1: tìm match chính xác
    for spec in specs:
        h_min = spec.get("height_min_cm")
        h_max = spec.get("height_max_cm")
        w_min = spec.get("weight_min_kg")
        w_max = spec.get("weight_max_kg")

        # Nếu spec không có range nào thì bỏ qua (không đủ dữ liệu để tra)
        if h_min is None and h_max is None and w_min is None and w_max is None:
            continue

        height_ok = (
            (h_min is None and h_max is None)  # shop không nhập height range
            or (h_min is not None and h_max is not None and h_min <= height_cm <= h_max)
        )
        weight_ok = (
            (w_min is None and w_max is None)  # shop không nhập weight range
            or (w_min is not None and w_max is not None and w_min <= weight_kg <= w_max)
        )

        if height_ok and weight_ok:
            return spec.get("size_label")

    # Pass 2: fallback — tìm spec gần nhất theo weight nếu có weight range
    closest_size = None
    min_dist = float("inf")
    for spec in specs:
        w_min = spec.get("weight_min_kg")
        w_max = spec.get("weight_max_kg")
        if w_min is None or w_max is None:
            continue
        dist = max(0, w_min - weight_kg, weight_kg - w_max)
        if dist < min_dist:
            min_dist = dist
            closest_size = spec.get("size_label")

    return closest_size


# ══════════════════════════════════════════════════════════════════════════════
# CORE PUBLIC FUNCTIONS (stateless — testable độc lập)
# ══════════════════════════════════════════════════════════════════════════════

def assess_fit_detail(
    body: dict,
    specs: list[dict],
    selected_size: Optional[str] = None,
) -> dict:
    """
    DETAIL mode: đánh giá fit dựa trên số đo chest/waist/hip.

    Args:
        body:          {"chest_cm": float, "waist_cm": float, "hip_cm": float}
        specs:         list[GarmentSizeSpec.to_dict()]
        selected_size: size label muốn kiểm tra (mặc định "M" hoặc size đầu tiên)

    Returns:
        {
            "mode": "detail",
            "selected_size": str,
            "available_sizes": list[str],
            "chest_fit":  {"diff_cm": float, "status": str},
            "waist_fit":  {"diff_cm": float, "status": str},
            "hip_fit":    {"diff_cm": float, "status": str},
            "overall_fit": str,
            "recommendation": str,
            "suggested_size": str | None,
        }
    """
    size_map  = {(s.get("size_label") or "").upper(): s for s in specs}
    available = _sorted_sizes(list(size_map.keys()))

    # Chọn size để đánh giá
    chosen = (selected_size or "M").upper()
    if chosen not in size_map:
        for s in SIZE_ORDER:
            if s in size_map:
                chosen = s
                break
        else:
            chosen = available[0] if available else "M"

    spec     = size_map.get(chosen, {})
    statuses: list[str] = []
    out: dict = {
        "mode":            "detail",
        "selected_size":   chosen,
        "available_sizes": available,
    }

    for region in ("chest", "waist", "hip"):
        b = body.get(f"{region}_cm")
        g = spec.get(f"{region}_cm")
        if b is None or g is None:
            out[f"{region}_fit"] = {"diff_cm": None, "status": "unknown"}
            continue
        diff   = round(float(g) - float(b), 2)
        status = _classify_ease(diff, region)
        statuses.append(status)
        out[f"{region}_fit"] = {"diff_cm": diff, "status": status}

    overall              = _aggregate_overall(statuses)
    out["overall_fit"]   = overall
    out["recommendation"] = RECOMMENDATIONS[overall]
    out["suggested_size"] = _suggest_size_from_specs(body, specs)
    return out


def assess_fit_basic(
    height_cm: float,
    weight_kg: float,
    specs: list[dict],
) -> dict:
    """
    BASIC mode: gợi ý size theo height + weight dựa trên bảng của garment.

    Args:
        height_cm: chiều cao user (cm)
        weight_kg: cân nặng user (kg)
        specs:     list[GarmentSizeSpec.to_dict()] — bảng size của garment

    Returns:
        {
            "mode": "basic",
            "suggested_size": str | None,
            "available_sizes": list[str],
            "recommendation": str,
            "note": str,
        }
    """
    size      = _basic_size_lookup(height_cm, weight_kg, specs)
    available = _sorted_sizes([s.get("size_label", "") for s in specs])

    # Kiểm tra garment có nhập range khuyến nghị không
    has_basic_chart = any(
        s.get("height_min_cm") or s.get("weight_min_kg") for s in specs
    )

    if not has_basic_chart:
        note = "Sản phẩm này chưa có bảng khuyến nghị chiều cao/cân nặng. Hãy nhập số đo vòng ngực/eo/hông để được gợi ý chính xác hơn."
    else:
        note = "Dựa trên bảng size của sản phẩm. Để chính xác hơn, hãy nhập số đo vòng ngực/eo/hông."

    return {
        "mode":            "basic",
        "suggested_size":  size,
        "available_sizes": available,
        "recommendation":  (
            f"Dựa trên chiều cao {height_cm}cm và cân nặng {weight_kg}kg, size phù hợp là {size}."
            if size else
            "Không tìm được size phù hợp — thử nhập số đo chi tiết để có kết quả tốt hơn."
        ),
        "note": note,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE CLASS (DB-aware)
# ══════════════════════════════════════════════════════════════════════════════

class FitAssessmentService:
    """
    Orchestrate: load dữ liệu từ DB → gọi assess_fit_detail / assess_fit_basic.

    Ưu tiên DETAIL mode nếu user có đủ số đo chi tiết VÀ garment có size chart.
    Fallback BASIC mode nếu chỉ có height + weight.
    """

    def __init__(
        self,
        body_profile_repo: BodyProfileRepository,
        size_spec_repo: GarmentSizeSpecRepository,
    ):
        self.body_profile_repo = body_profile_repo
        self.size_spec_repo    = size_spec_repo

    @staticmethod
    def _profile_to_body_dict(profile) -> dict:
        def f(v):
            return float(v) if v is not None else None
        return {
            "height_cm": f(profile.height),
            "weight_kg": f(profile.weight),
            "chest_cm":  f(profile.chest),
            "waist_cm":  f(profile.waist),
            "hip_cm":    f(profile.hip),
            "gender":    profile.gender or "neutral",
        }

    @staticmethod
    def _has_detail_measurements(body: dict) -> bool:
        """True nếu có ít nhất 2 trong 3 số đo chi tiết."""
        return sum(
            1 for r in ("chest_cm", "waist_cm", "hip_cm")
            if body.get(r) is not None
        ) >= 2

    async def suggest(
        self,
        garment_id: int,
        user_id: Optional[int] = None,
        guest_measurements: Optional[dict] = None,
        selected_size: Optional[str] = None,
    ) -> dict:
        """
        Gợi ý size cho garment dựa trên thông tin cơ thể.

        Args:
            garment_id:         ID garment cần đánh giá
            user_id:            ID user đã đăng nhập (load profile từ DB)
            guest_measurements: số đo nhập tay nếu chưa lưu profile
                                 {"height_cm": 165, "weight_kg": 55}
                                 hoặc {"chest_cm": 86, "waist_cm": 68, "hip_cm": 92}
            selected_size:      size muốn kiểm tra cụ thể (optional)
        """
        # ── 1. Resolve body measurements ─────────────────────────────────────
        if user_id is not None:
            profile = await self.body_profile_repo.get_by_user_id(user_id)
            if not profile:
                raise HTTPException(
                    status_code=404,
                    detail="Chưa có thông tin cơ thể. Vui lòng cập nhật body profile hoặc nhập tay.",
                )
            body = self._profile_to_body_dict(profile)
        elif guest_measurements:
            body = {
                "height_cm": guest_measurements.get("height_cm"),
                "weight_kg": guest_measurements.get("weight_kg"),
                "chest_cm":  guest_measurements.get("chest_cm"),
                "waist_cm":  guest_measurements.get("waist_cm"),
                "hip_cm":    guest_measurements.get("hip_cm"),
                "gender":    guest_measurements.get("gender", "neutral"),
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Cần cung cấp user_id hoặc measurements.",
            )

        # ── 2. Load size specs của garment ────────────────────────────────────
        specs     = await self.size_spec_repo.get_by_garment_id(garment_id)
        specs_dict = [s.to_dict() for s in specs]

        if not specs:
            raise HTTPException(
                status_code=422,
                detail="Sản phẩm này chưa có bảng size. Vui lòng liên hệ shop.",
            )

        # ── 3. Chọn mode ──────────────────────────────────────────────────────
        if self._has_detail_measurements(body):
            # DETAIL: có đủ số đo chi tiết → tính ease
            result = assess_fit_detail(
                body=body,
                specs=specs_dict,
                selected_size=selected_size,
            )
        elif body.get("height_cm") and body.get("weight_kg"):
            # BASIC: chỉ có height + weight → tra bảng garment
            result = assess_fit_basic(
                height_cm=float(body["height_cm"]),
                weight_kg=float(body["weight_kg"]),
                specs=specs_dict,
            )
        else:
            raise HTTPException(
                status_code=422,
                detail="Cần ít nhất height + weight, hoặc 2 trong 3 số đo chest/waist/hip.",
            )

        # ── 4. Đính kèm thông tin thêm ────────────────────────────────────────
        result["body_measurements"] = {k: v for k, v in body.items() if v is not None}
        result["garment_id"]        = garment_id
        result["has_size_chart"]    = True
        return result