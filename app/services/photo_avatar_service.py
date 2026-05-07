"""
photo_avatar_service.py
-----------------------
Mục đích: Quản lý việc tạo avatar 3D cho user.

So với version cũ, version này thêm:
1. Trigger body mesh generation chạy ngầm (background task)
2. Warm start — tìm beta gần nhất trong DB trước khi optimization
3. Cập nhật status avatar (processing → ready / failed) sau khi xong
"""

import asyncio
import logging
from typing import Optional

from fastapi import HTTPException

from models.photo_avatar import PhotoAvatar
from repositories.body_profile_repository import BodyProfileRepository
from repositories.photo_avatar_repository import PhotoAvatarRepository
from repositories.user_repository import UserRepository
from services.ml.body_mesh_service import generate_body_mesh

logger = logging.getLogger(__name__)


class PhotoAvatarService:
    def __init__(
        self,
        repo: PhotoAvatarRepository,
        user_repo: UserRepository,
        body_profile_repo: BodyProfileRepository,
    ):
        self.repo = repo
        self.user_repo = user_repo
        self.body_profile_repo = body_profile_repo

    async def create_avatar_job(
        self, user_id: int, body_profile_id: Optional[int] = None
    ) -> PhotoAvatar:
        """
        Tạo avatar job và kick off background task.

        Luồng:
        1. Validate user + body profile tồn tại
        2. Tạo record avatar với status="processing" trong DB
        3. Trả về avatar record NGAY LẬP TỨC cho client (không chờ ML xong)
        4. Đồng thời kick off background task chạy optimization + export GLB
        5. Khi background task xong → cập nhật status="ready" + glb_url vào DB

        Tại sao trả về ngay mà không chờ:
        Optimization mất ~1 giây, export GLB mất thêm ~1-2 giây, upload
        Cloudinary mất ~1-2 giây nữa. Tổng ~3-5 giây. Nếu bắt client chờ
        thì UX rất tệ. Thay vào đó trả về job_id ngay, client dùng
        GET /avatar/{id} để poll status cho đến khi "ready".
        """
        # ── Validate user ──────────────────────────────────────────────────
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Khong tim thay user")

        # ── Validate body profile ──────────────────────────────────────────
        profile = None
        if body_profile_id is not None:
            profile = await self.body_profile_repo.get_by_id(body_profile_id)
            if not profile:
                raise HTTPException(
                    status_code=404, detail="Khong tim thay body profile"
                )
            if profile.user_id != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Body profile khong thuoc ve user nay",
                )

        # ── Tạo avatar record với status=processing ────────────────────────
        # Client nhận record này ngay lập tức
        avatar = await self.repo.create(
            user_id=user_id,
            body_profile_id=body_profile_id,
        )

        # ── Kick off background task nếu có body profile ──────────────────
        # asyncio.create_task: chạy hàm bất đồng bộ ngầm, không block response
        if profile is not None:
            asyncio.create_task(
                self._run_body_mesh_background(
                    avatar_id=avatar.id,
                    profile=profile,
                    user_id=user_id,
                )
            )
            logger.info(
                f"Background task kicked off cho avatar_id={avatar.id}"
            )
        else:
            # Không có body profile → không thể tạo mesh
            # Avatar vẫn được tạo nhưng status giữ nguyên "processing"
            # đợi client gửi body profile sau
            logger.warning(
                f"Avatar {avatar.id} tạo không có body profile, "
                "bỏ qua body mesh generation"
            )

        return avatar

    async def _run_body_mesh_background(
        self,
        avatar_id: int,
        profile,
        user_id: int,
    ) -> None:
        """
        Chạy ngầm: optimization → export GLB → upload → cập nhật DB.

        Hàm này KHÔNG được gọi trực tiếp từ router.
        Nó được asyncio.create_task() gọi tự động sau khi create_avatar_job
        trả về response cho client.

        Tại sao có try/except bao toàn bộ:
        Background task nếu crash mà không catch thì lỗi bị nuốt im lặng,
        avatar sẽ kẹt ở status="processing" mãi mãi. Catch lỗi → cập nhật
        status="failed" → client biết để retry.
        """
        try:
            logger.info(f"Bắt đầu body mesh cho avatar_id={avatar_id}")

            # ── Kiểm tra cache ─────────────────────────────────────────────
            # Nếu profile đã có beta_cache từ trước (cùng số đo) → dùng lại
            cached_beta = None
            if profile.beta_cache and isinstance(profile.beta_cache, dict):
                cached_beta = profile.beta_cache.get("betas")
                if cached_beta:
                    logger.info(
                        f"Cache hit: dùng beta cũ cho profile_id={profile.id}"
                    )

            # ── Warm start ─────────────────────────────────────────────────
            # Tìm người trong DB có số đo gần nhất → dùng beta của họ
            # để khởi động optimization nhanh hơn
            warm_start_beta = None
            if cached_beta is None:
                warm_start_beta = await self.body_profile_repo.find_nearest_beta(
                    height=float(profile.height or 0),
                    chest=float(profile.chest or 0),
                    waist=float(profile.waist or 0),
                    hip=float(profile.hip or 0),
                    gender=profile.gender,
                    exclude_user_id=user_id,
                )
                if warm_start_beta:
                    logger.info("Warm start tìm được beta gần nhất")
                else:
                    logger.info("Không có warm start, dùng cold start")

            # ── Chạy optimization + export GLB ────────────────────────────
            result = await generate_body_mesh(
                height=float(profile.height or 170),
                chest=float(profile.chest or 90),
                waist=float(profile.waist or 70),
                hip=float(profile.hip or 95),
                shoulder=float(profile.shoulder or 40),
                arm_length=float(profile.arm_length or 60),
                inseam=float(profile.inseam or 75),
                gender=profile.gender,
                cached_beta=cached_beta,
                warm_start_beta=warm_start_beta,
            )

            # ── Lưu beta vào body profile để cache cho lần sau ─────────────
            await self.body_profile_repo.update_beta_cache(
                profile_id=profile.id,
                beta_cache={"betas": result.beta},
                beta_hash=result.beta_hash,
            )

            # ── Cập nhật avatar: status=ready + glb_url ───────────────────
            await self.repo.update(
                avatar_id=avatar_id,
                body_glb_url=result.glb_url,
                status="ready",
            )

            logger.info(
                f"Avatar {avatar_id} ready sau {result.iterations} iterations, "
                f"from_cache={result.from_cache}"
            )

        except Exception as e:
            # Bất kỳ lỗi nào → đánh dấu failed để client biết retry
            logger.error(
                f"Body mesh thất bại cho avatar_id={avatar_id}: {e}",
                exc_info=True,
            )
            try:
                await self.repo.update(
                    avatar_id=avatar_id,
                    status="failed",
                )
            except Exception as update_err:
                logger.error(
                    f"Không thể update status=failed: {update_err}"
                )

    async def get_avatar(
        self, avatar_id: int, user_id: int
    ) -> Optional[PhotoAvatar]:
        """
        Lấy thông tin avatar theo id.

        Client dùng endpoint này để poll status:
        - status="processing" → đang chạy, chờ thêm
        - status="ready"      → có glb_url, load Babylon.js được rồi
        - status="failed"     → lỗi, cho phép retry
        """
        avatar = await self.repo.get_by_id(avatar_id)
        if not avatar:
            return None
        if avatar.user_id != user_id:
            raise HTTPException(
                status_code=403, detail="Avatar khong thuoc ve user nay"
            )
        return avatar