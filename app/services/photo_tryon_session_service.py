from typing import Optional

from fastapi import HTTPException

from repositories.body_profile_repository import BodyProfileRepository
from repositories.garment_drape_repository import GarmentDrapeRepository
from repositories.garment_repository import GarmentRepository
from repositories.photo_avatar_repository import PhotoAvatarRepository
from repositories.photo_tryon_session_repository import PhotoTryonSessionRepository
from schemas.photo_tryon_session import FitWarning, TryonResponse


SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]
FIT_RULES = {
    "chest": {"ease_min": 4.0, "ease_max": 12.0, "tight_threshold": -2.0},
    "waist": {"ease_min": 2.0, "ease_max": 10.0, "tight_threshold": -2.0},
    "hip": {"ease_min": 4.0, "ease_max": 12.0, "tight_threshold": -2.0},
    "shoulder": {"ease_min": -1.0, "ease_max": 3.0, "tight_threshold": -2.0},
    "arm_length": {"ease_min": -2.0, "ease_max": 4.0, "tight_threshold": -3.0},
    "inseam": {"ease_min": -2.0, "ease_max": 4.0, "tight_threshold": -3.0},
}


class PhotoTryonSessionService:
    def __init__(
        self,
        repo: PhotoTryonSessionRepository,
        avatar_repo: PhotoAvatarRepository,
        garment_repo: GarmentRepository,
        body_profile_repo: BodyProfileRepository,
        garment_drape_repo: GarmentDrapeRepository,
    ):
        self.repo = repo
        self.avatar_repo = avatar_repo
        self.garment_repo = garment_repo
        self.body_profile_repo = body_profile_repo
        self.garment_drape_repo = garment_drape_repo

    @staticmethod
    def _to_float(value) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _evaluate_size(
        cls, measurements: dict, size_spec: dict
    ) -> tuple[list[FitWarning], float]:
        warnings: list[FitWarning] = []
        score = 0.0
        for field, rules in FIT_RULES.items():
            body_value = cls._to_float(measurements.get(field))
            garment_value = cls._to_float(size_spec.get(field))
            if body_value is None or garment_value is None:
                continue
            delta = round(garment_value - body_value, 2)
            ease_min = rules["ease_min"]
            ease_max = rules["ease_max"]
            tight = rules["tight_threshold"]

            if delta < tight:
                warnings.append(
                    FitWarning(
                        severity="error",
                        message=f"{field} qua chat ({abs(delta):.1f}cm thieu)",
                        delta_cm=delta,
                    )
                )
                score += (tight - delta) ** 2 + 25
            elif delta < ease_min:
                warnings.append(
                    FitWarning(
                        severity="warning",
                        message=f"{field} hoi chat ({abs(delta):.1f}cm thieu)",
                        delta_cm=delta,
                    )
                )
                score += (ease_min - delta) ** 2
            elif delta > ease_max:
                warnings.append(
                    FitWarning(
                        severity="warning",
                        message=f"{field} hoi rong ({delta:.1f}cm du)",
                        delta_cm=delta,
                    )
                )
                score += (delta - ease_max) ** 2
        return warnings, score

    @classmethod
    def check_garment_fit(
        cls,
        measurements: dict,
        sizes_spec: dict,
        selected_size: str,
    ) -> tuple[list[FitWarning], Optional[str]]:
        if not sizes_spec:
            return [], None

        scores: dict[str, float] = {}
        warnings_per_size: dict[str, list[FitWarning]] = {}
        for size, spec in sizes_spec.items():
            if not isinstance(spec, dict):
                continue
            warnings, score = cls._evaluate_size(measurements, spec)
            warnings_per_size[size] = warnings
            scores[size] = score

        if not scores:
            return [], None

        suggested_size = min(scores, key=lambda s: (scores[s], cls._size_rank(s)))
        selected_warnings = warnings_per_size.get(selected_size, [])
        return selected_warnings, suggested_size

    @staticmethod
    def _size_rank(size: str) -> int:
        upper = size.upper() if isinstance(size, str) else ""
        return SIZE_ORDER.index(upper) if upper in SIZE_ORDER else len(SIZE_ORDER)

    @staticmethod
    def _measurements_from_profile(profile) -> dict:
        return {
            "height": profile.height,
            "weight": profile.weight,
            "chest": profile.chest,
            "waist": profile.waist,
            "hip": profile.hip,
            "shoulder": profile.shoulder,
            "arm_length": profile.arm_length,
            "inseam": profile.inseam,
        }

    async def create_tryon_session(
        self,
        user_id: Optional[int],
        avatar_id: int,
        garment_id: int,
        selected_size: str,
    ) -> TryonResponse:
        avatar = await self.avatar_repo.get_by_id(avatar_id)
        if not avatar:
            raise HTTPException(status_code=404, detail="Khong tim thay avatar")
        if user_id is not None and avatar.user_id != user_id:
            raise HTTPException(
                status_code=403, detail="Avatar khong thuoc ve user nay"
            )

        garment = await self.garment_repo.get_by_id(garment_id)
        if not garment:
            raise HTTPException(status_code=404, detail="Khong tim thay garment")

        measurements: dict = {}
        beta_hash: Optional[str] = None
        if avatar.body_profile_id:
            profile = await self.body_profile_repo.get_by_id(avatar.body_profile_id)
            if profile:
                measurements = self._measurements_from_profile(profile)
                beta_hash = profile.beta_hash

        sizes_spec = getattr(garment, "sizes", None) or {}
        warnings, suggested_size = self.check_garment_fit(
            measurements, sizes_spec, selected_size
        )

        garment_drape_glb_url: Optional[str] = None
        heatmap_glb_url: Optional[str] = None
        if beta_hash:
            cached = await self.garment_drape_repo.get_cached(
                garment_id=garment_id,
                beta_hash=beta_hash,
                size=selected_size,
            )
            if cached:
                garment_drape_glb_url = cached.glb_url
                heatmap_glb_url = cached.heatmap_glb_url

        warnings_payload = [w.model_dump() for w in warnings]
        session = await self.repo.create(
            user_id=user_id,
            avatar_id=avatar_id,
            garment_id=garment_id,
            selected_size=selected_size,
            suggested_size=suggested_size,
            fit_warnings=warnings_payload,
        )

        return TryonResponse(
            session_id=session.id,
            avatar_id=avatar_id,
            garment_id=garment_id,
            selected_size=selected_size,
            suggested_size=suggested_size,
            fit_warnings=warnings,
            garment_drape_glb_url=garment_drape_glb_url,
            heatmap_glb_url=heatmap_glb_url,
        )

    async def get_user_sessions(self, user_id: int):
        return await self.repo.get_by_user_id(user_id)
