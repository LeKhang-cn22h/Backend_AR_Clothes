import hashlib
import json

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from models.body_profile import BodyProfile
from repositories.body_profile_repository import BodyProfileRepository
from repositories.user_repository import UserRepository
from schemas.body_profile import BodyProfileCreate


class BodyProfileService:
    MEASUREMENT_FIELDS = (
        "height",
        "weight",
        "chest",
        "waist",
        "hip",
        "shoulder",
        "arm_length",
        "inseam",
    )

    def __init__(
        self,
        repo: BodyProfileRepository,
        user_repo: UserRepository,
    ):
        self.repo = repo
        self.user_repo = user_repo

    @classmethod
    def compute_beta_hash(cls, data: dict) -> str:
        payload = {}
        for field in sorted(cls.MEASUREMENT_FIELDS):
            value = data.get(field)
            payload[field] = float(value) if value is not None else None
        payload["gender"] = data.get("gender", "neutral")
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()[:16]

    async def create_or_update_profile(
        self, user_id: int, data: BodyProfileCreate
    ) -> BodyProfile:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Khong tim thay user")

        payload = data.model_dump()
        beta_hash = self.compute_beta_hash(payload)

        existing = await self.repo.get_by_user_id(user_id)
        if existing:
            return await self.repo.update(
                existing.id,
                beta_hash=beta_hash,
                beta_cache=None,
                **payload,
            )

        return await self.repo.create(
            user_id=user_id,
            data={**payload, "beta_hash": beta_hash, "beta_cache": None},
        )
