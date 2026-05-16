"""
head_body_merge_service.py
--------------------------
Ghép head mesh (DECA, FLAME topology) vào body mesh (SMPL-X) tại neck joint.

Pipeline:
    body_glb_url  ──► trimesh load
    head_glb_bytes ──► trimesh load
        ► tìm neck position (SMPL-X joint 12 = neck)
        ► translate head centroid → neck
        ► scale head theo bounding-box body
        ► concatenate → merged Trimesh
        ► export GLB → upload Cloudinary
"""

import asyncio
import io
import logging
import os
import tempfile
from typing import Optional

import cloudinary.uploader
import numpy as np
import trimesh
from urllib.request import urlopen

logger = logging.getLogger(__name__)

# SMPL-X joint index 12 = neck (chuẩn smplx.JOINT_NAMES)
SMPLX_NECK_JOINT_IDX = 12


# ══════════════════════════════════════════════════════════════════════════════
# LOAD MESH HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _load_mesh_from_url(url: str) -> trimesh.Trimesh:
    """Tải GLB từ URL (Cloudinary) và trả về single Trimesh.

    trimesh.load có thể trả về Scene; ta gộp về Trimesh đơn để dễ ghép.
    """
    with urlopen(url) as resp:
        data = resp.read()
    return _load_mesh_from_bytes(data, "glb")


def _load_mesh_from_bytes(data: bytes, file_type: str = "glb") -> trimesh.Trimesh:
    obj = trimesh.load(io.BytesIO(data), file_type=file_type, force="mesh")
    if isinstance(obj, trimesh.Scene):
        # Gộp tất cả geometry trong scene
        meshes = [g for g in obj.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if not meshes:
            raise ValueError("GLB scene không chứa mesh nào")
        obj = trimesh.util.concatenate(meshes)
    if not isinstance(obj, trimesh.Trimesh):
        raise ValueError(f"Không đọc được mesh từ GLB ({type(obj)})")
    return obj


# ══════════════════════════════════════════════════════════════════════════════
# ALIGNMENT
# ══════════════════════════════════════════════════════════════════════════════

def _align_head_to_neck(
    head: trimesh.Trimesh,
    body: trimesh.Trimesh,
    neck_pos: np.ndarray,
) -> trimesh.Trimesh:
    """
    1. Scale head sao cho chiều cao head ≈ 0.22 * chiều cao body
       (anthropometric ratio: head ~ 1/4.5 thân, lấy 0.22 cho an toàn).
    2. Translate centroid head → neck position trên body.
    """
    head = head.copy()

    body_bbox = body.bounds                          # [[xmin,..],[xmax,..]]
    head_bbox = head.bounds
    body_height = float(body_bbox[1, 1] - body_bbox[0, 1])
    head_height = float(head_bbox[1, 1] - head_bbox[0, 1])

    if head_height <= 1e-6:
        raise ValueError("Head mesh có chiều cao ~0, không scale được")

    target_head_height = 0.22 * body_height
    scale = target_head_height / head_height
    head.apply_scale(scale)

    # Sau scale, centroid mới → cần translate sao cho điểm đáy head ≈ neck
    head_bbox = head.bounds
    head_bottom_center = np.array([
        (head_bbox[0, 0] + head_bbox[1, 0]) / 2.0,
        head_bbox[0, 1],                              # y_min của head
        (head_bbox[0, 2] + head_bbox[1, 2]) / 2.0,
    ], dtype=np.float64)

    translation = np.asarray(neck_pos, dtype=np.float64) - head_bottom_center
    head.apply_translation(translation)
    return head


# ══════════════════════════════════════════════════════════════════════════════
# UPLOAD CLOUDINARY
# ══════════════════════════════════════════════════════════════════════════════

def _upload_glb_to_cloudinary(glb_path: str, public_id: str) -> str:
    try:
        result = cloudinary.uploader.upload(
            glb_path,
            resource_type="raw",
            folder="merged_avatars",
            public_id=public_id,
            overwrite=True,
        )
        return result["secure_url"]
    finally:
        if os.path.exists(glb_path):
            os.unlink(glb_path)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def _merge_sync(
    body_glb_url: str,
    head_glb_bytes: bytes,
    neck_joint_pos: np.ndarray,
    public_id: str,
) -> str:
    body = _load_mesh_from_url(body_glb_url)
    head = _load_mesh_from_bytes(head_glb_bytes, "glb")

    head_aligned = _align_head_to_neck(head, body, np.asarray(neck_joint_pos))
    merged = trimesh.util.concatenate([body, head_aligned])
    if not isinstance(merged, trimesh.Trimesh):
        raise ValueError("Concatenate không trả về Trimesh")

    tmp = tempfile.NamedTemporaryFile(suffix=".glb", delete=False)
    tmp.close()
    merged.export(tmp.name)
    return _upload_glb_to_cloudinary(tmp.name, public_id)


async def merge_head_body(
    body_glb_url: str,
    head_glb_bytes: bytes,
    neck_joint_pos: np.ndarray,
    public_id: Optional[str] = None,
) -> str:
    """
    Ghép head + body, upload Cloudinary, trả về secure_url của merged GLB.

    Args:
        body_glb_url:    Cloudinary URL của body GLB
        head_glb_bytes:  GLB bytes từ DECA reconstruct_face
        neck_joint_pos:  np.ndarray [x, y, z] — vị trí neck joint từ SMPL-X
        public_id:       optional — đặt tên file trên Cloudinary

    Returns:
        Cloudinary secure_url của merged GLB
    """
    if public_id is None:
        # hash đơn giản theo url + bytes để cache cùng input → cùng output
        import hashlib
        h = hashlib.md5(body_glb_url.encode() + head_glb_bytes[:1024]).hexdigest()[:16]
        public_id = f"merged_{h}"

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _merge_sync, body_glb_url, head_glb_bytes,
        np.asarray(neck_joint_pos), public_id,
    )


# ══════════════════════════════════════════════════════════════════════════════
# NECK JOINT EXTRACTION (helper cho router)
# ══════════════════════════════════════════════════════════════════════════════

def get_neck_joint_position(
    beta: list[float], gender: str
) -> np.ndarray:
    """Forward SMPL-X với beta đã có để lấy vị trí neck joint (index 12).

    Trả về np.ndarray [3] đơn vị mét trong space mesh.
    """
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
    joints = out.joints[0].numpy()                          # [J, 3]
    return joints[SMPLX_NECK_JOINT_IDX].astype(np.float32)
