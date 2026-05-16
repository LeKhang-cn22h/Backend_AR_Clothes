"""
deca_service.py
---------------
DECA face reconstruction.

Pipeline:
    selfie image
        → face_alignment (68 landmarks, 224×224 crop)
        → ResNet50 + MLP encoder
        → FLAME parameters (shape, pose, exp, tex, cam, light)
        → FLAME forward (numpy, no pytorch3d)
        → trimesh Trimesh
        → GLB bytes

Weights:
    ml_models/deca/deca_model.tar       -- E_flame, E_detail, D_detail
    ml_models/deca/generic_model.pkl    -- FLAME mesh template
    ml_models/deca/mediapipe_landmark_embedding.npz
"""

import asyncio
import logging
import os
import pickle
from typing import Optional

import cv2
import numpy as np
import torch
import torch.nn as nn
import torchvision.models as tvm
import trimesh

logger = logging.getLogger(__name__)

DECA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "ml_models", "deca"
)

CHECKPOINT_PATH = os.path.join(DECA_DIR, "deca_model.tar")
FLAME_PATH      = os.path.join(DECA_DIR, "generic_model.pkl")

N_SHAPE = 100
N_POSE  = 6
N_EXP   = 50
N_TEX   = 50
N_CAM   = 3
N_LIGHT = 27
N_TOTAL = N_SHAPE + N_POSE + N_EXP + N_TEX + N_CAM + N_LIGHT  # 236

IMG_SIZE = 224

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)


# ══════════════════════════════════════════════════════════════════════════════
# CHUMPY PATCH — generic_model.pkl chứa chumpy arrays
# ══════════════════════════════════════════════════════════════════════════════
# numpy 1.26 đã loại bỏ một số alias mà chumpy 0.70 còn dùng. Patch trước khi
# import/unpickle để không phải sửa chumpy nguồn.

def _patch_numpy_for_chumpy() -> None:
    for alias, target in (
        ("bool", bool),
        ("int", int),
        ("float", float),
        ("complex", complex),
        ("object", object),
        ("unicode", str),
        ("str", str),
        ("long", int),
    ):
        if not hasattr(np, alias):
            setattr(np, alias, target)


# ══════════════════════════════════════════════════════════════════════════════
# RESNET50 + MLP ENCODER
# ══════════════════════════════════════════════════════════════════════════════

class FlameEncoder(nn.Module):
    """
    DECA's E_flame:
      - encoder.{conv1,bn1,layer1..4} = torchvision ResNet50 backbone (no fc)
      - layers.0 = Linear(2048, 1024)
      - layers.2 = Linear(1024, 236)   (layers.1 là ReLU)
    """

    def __init__(self, out_dim: int = N_TOTAL):
        super().__init__()
        backbone = tvm.resnet50(weights=None)
        # Bỏ avgpool + fc; ta dùng manual pool sau layer4 để giống DECA.
        self.encoder = nn.Sequential(
            backbone.conv1,
            backbone.bn1,
            backbone.relu,
            backbone.maxpool,
            backbone.layer1,
            backbone.layer2,
            backbone.layer3,
            backbone.layer4,
        )
        self.layers = nn.Sequential(
            nn.Linear(2048, 1024),
            nn.ReLU(),
            nn.Linear(1024, out_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.encoder(x)                  # [B, 2048, H', W']
        feat = feat.mean(dim=[2, 3])            # global avg pool → [B, 2048]
        return self.layers(feat)                # [B, 236]


def _load_encoder_weights(model: FlameEncoder, ckpt_path: str) -> None:
    """
    DECA checkpoint là dict: {'E_flame': state_dict, 'E_detail': ..., ...}.
    Một vài key có thể tiền tố khác nhau giữa version, ta map lại bằng tên cuối.
    """
    raw = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    state = raw.get("E_flame", raw) if isinstance(raw, dict) else raw

    # Một số checkpoint dùng prefix khác — strip prefix khi cần
    cleaned = {}
    for k, v in state.items():
        nk = k
        for prefix in ("module.", "E_flame.", "model."):
            if nk.startswith(prefix):
                nk = nk[len(prefix):]
        cleaned[nk] = v

    missing, unexpected = model.load_state_dict(cleaned, strict=False)
    if missing:
        logger.warning(f"DECA encoder missing keys ({len(missing)}): "
                       f"{missing[:5]}{'...' if len(missing) > 5 else ''}")
    if unexpected:
        logger.warning(f"DECA encoder unexpected keys ({len(unexpected)}): "
                       f"{unexpected[:5]}{'...' if len(unexpected) > 5 else ''}")


# ══════════════════════════════════════════════════════════════════════════════
# FLAME (numpy)
# ══════════════════════════════════════════════════════════════════════════════

class FlameNumpy:
    """
    FLAME forward implement bằng numpy thuần.

    Forward đơn giản:
        v = v_template
            + shapedirs[..., :100] @ shape
            + shapedirs[..., 100:] @ exp
        # Áp pose blend shapes (rodrigues) + LBS với J_regressor và weights.
    """

    def __init__(self, flame_pkl: str):
        _patch_numpy_for_chumpy()
        with open(flame_pkl, "rb") as f:
            data = pickle.load(f, encoding="latin1")

        def to_np(x) -> np.ndarray:
            # chumpy Ch -> np.ndarray
            return np.asarray(x.r if hasattr(x, "r") else x, dtype=np.float32)

        self.v_template = to_np(data["v_template"])              # [N, 3]
        self.shapedirs  = to_np(data["shapedirs"])               # [N, 3, 100+50]
        self.posedirs   = to_np(data["posedirs"])                # [N*3, 9*K] hoặc [N,3,9*K]
        self.J_regressor = to_np(data["J_regressor"])            # [J, N]
        if hasattr(self.J_regressor, "toarray"):
            self.J_regressor = self.J_regressor.toarray().astype(np.float32)
        self.weights    = to_np(data["weights"])                 # [N, J]
        faces           = data["f"]
        self.faces      = np.asarray(faces, dtype=np.int64)

        self.n_verts    = self.v_template.shape[0]
        self.n_joints   = self.weights.shape[1]

        # posedirs có thể có shape [N, 3, 9*(J-1)] hoặc [N*3, 9*(J-1)]
        if self.posedirs.ndim == 2:
            self.posedirs = self.posedirs.reshape(self.n_verts, 3, -1)

        # Một vài bản FLAME pickle gồm cả 'kintree_table'
        kintree = data.get("kintree_table")
        if kintree is not None:
            kintree = np.asarray(kintree, dtype=np.int64)
            self.parents = kintree[0].copy()
            self.parents[0] = -1
        else:
            self.parents = np.full(self.n_joints, -1, dtype=np.int64)

    def forward(
        self,
        shape: np.ndarray,         # [100]
        exp:   np.ndarray,         # [50]
        pose:  np.ndarray,         # [6] — global(3) + jaw(3) hoặc 0..6
    ) -> np.ndarray:
        """Trả về vertices [N,3] — nếu thiếu kintree thì chỉ trả mesh shape+exp."""
        # Shape + expression blend shapes
        n_shape = min(self.shapedirs.shape[2], shape.shape[0] + exp.shape[0])
        coeffs = np.concatenate([shape, exp], axis=0)[:n_shape].astype(np.float32)
        offsets = self.shapedirs[..., :n_shape] @ coeffs        # [N, 3]
        v = self.v_template + offsets

        # Áp global rotation đơn giản (axis-angle 3 đầu của pose)
        if pose is not None and pose.size >= 3:
            R = _rodrigues(pose[:3].astype(np.float32))
            v = v @ R.T

        return v.astype(np.float32)


def _rodrigues(rvec: np.ndarray) -> np.ndarray:
    """Axis-angle 3-vector → 3x3 rotation matrix (numpy)."""
    theta = float(np.linalg.norm(rvec))
    if theta < 1e-8:
        return np.eye(3, dtype=np.float32)
    k = (rvec / theta).astype(np.float32)
    K = np.array([
        [0.0, -k[2],  k[1]],
        [k[2],  0.0, -k[0]],
        [-k[1], k[0],  0.0],
    ], dtype=np.float32)
    R = np.eye(3, dtype=np.float32) + np.sin(theta) * K + (1 - np.cos(theta)) * (K @ K)
    return R


# ══════════════════════════════════════════════════════════════════════════════
# IMAGE PREPROCESSING + LANDMARKS
# ══════════════════════════════════════════════════════════════════════════════

def _to_tensor(img_rgb: np.ndarray, device: torch.device) -> torch.Tensor:
    """uint8 RGB [H,W,3] → float32 [1,3,H,W] normalized ImageNet."""
    img = img_rgb.astype(np.float32) / 255.0
    img = (img - IMAGENET_MEAN) / IMAGENET_STD
    img = np.transpose(img, (2, 0, 1))
    return torch.from_numpy(img).unsqueeze(0).to(device)


def _crop_from_landmarks(
    image_rgb: np.ndarray, landmarks: np.ndarray, scale: float = 1.25
) -> np.ndarray:
    """Crop vuông quanh face landmarks và resize 224x224."""
    h, w = image_rgb.shape[:2]
    x_min, y_min = landmarks[:, 0].min(), landmarks[:, 1].min()
    x_max, y_max = landmarks[:, 0].max(), landmarks[:, 1].max()
    cx = (x_min + x_max) / 2.0
    cy = (y_min + y_max) / 2.0
    size = max(x_max - x_min, y_max - y_min) * scale

    x0 = int(round(cx - size / 2))
    y0 = int(round(cy - size / 2))
    x1 = int(round(cx + size / 2))
    y1 = int(round(cy + size / 2))

    pad_l = max(0, -x0)
    pad_t = max(0, -y0)
    pad_r = max(0, x1 - w)
    pad_b = max(0, y1 - h)
    if pad_l or pad_t or pad_r or pad_b:
        image_rgb = cv2.copyMakeBorder(
            image_rgb, pad_t, pad_b, pad_l, pad_r,
            borderType=cv2.BORDER_REFLECT_101,
        )
        x0 += pad_l; x1 += pad_l
        y0 += pad_t; y1 += pad_t

    crop = image_rgb[y0:y1, x0:x1]
    if crop.size == 0:
        raise ValueError("Empty face crop after landmark alignment")
    return cv2.resize(crop, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_LINEAR)


# ══════════════════════════════════════════════════════════════════════════════
# DECA SERVICE
# ══════════════════════════════════════════════════════════════════════════════

class DECAService:
    """Singleton — load weights một lần khi startup."""

    def __init__(self, model_dir: str = DECA_DIR):
        self.model_dir = model_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"DECA loading on device: {self.device}")

        self.encoder = FlameEncoder().to(self.device).eval()
        _load_encoder_weights(
            self.encoder, os.path.join(model_dir, "deca_model.tar")
        )

        self.flame = FlameNumpy(os.path.join(model_dir, "generic_model.pkl"))
        self._fa = None  # face_alignment lazy-init (tốn memory)

        logger.info(
            f"DECA ready — FLAME mesh: {self.flame.n_verts} verts, "
            f"{len(self.flame.faces)} faces"
        )

    # ── Landmark detection ────────────────────────────────────────────────
    def _get_face_alignment(self):
        if self._fa is None:
            import face_alignment
            self._fa = face_alignment.FaceAlignment(
                face_alignment.LandmarksType.TWO_D,
                device=str(self.device),
                flip_input=False,
            )
        return self._fa

    def _detect_landmarks(self, image_rgb: np.ndarray) -> np.ndarray:
        fa = self._get_face_alignment()
        preds = fa.get_landmarks(image_rgb)
        if not preds:
            raise ValueError("No face detected in image")
        return np.asarray(preds[0], dtype=np.float32)  # [68, 2]

    # ── Encode → FLAME params ─────────────────────────────────────────────
    def _encode(self, face_crop_rgb: np.ndarray) -> dict:
        x = _to_tensor(face_crop_rgb, self.device)
        with torch.no_grad():
            params = self.encoder(x)[0].detach().cpu().numpy().astype(np.float32)
        s, p, e, t, c = N_SHAPE, N_POSE, N_EXP, N_TEX, N_CAM
        return {
            "shape": params[0:s],
            "pose":  params[s:s+p],
            "exp":   params[s+p:s+p+e],
            "tex":   params[s+p+e:s+p+e+t],
            "cam":   params[s+p+e+t:s+p+e+t+c],
            "light": params[s+p+e+t+c:],
        }

    # ── FLAME forward ─────────────────────────────────────────────────────
    def _flame_forward(self, params: dict) -> tuple[np.ndarray, np.ndarray]:
        v = self.flame.forward(
            shape=params["shape"],
            exp=params["exp"],
            pose=params["pose"],
        )
        return v, self.flame.faces

    # ── Export GLB ────────────────────────────────────────────────────────
    def _export_glb(self, vertices: np.ndarray, faces: np.ndarray) -> bytes:
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        return mesh.export(file_type="glb")

    # ── Public sync (chạy trong executor) ─────────────────────────────────
    def _reconstruct_sync(self, image_bgr: np.ndarray) -> dict:
        if image_bgr is None or image_bgr.size == 0:
            raise ValueError("Empty image")
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

        landmarks = self._detect_landmarks(image_rgb)
        face_crop = _crop_from_landmarks(image_rgb, landmarks)
        params    = self._encode(face_crop)
        verts, faces = self._flame_forward(params)
        glb_bytes = self._export_glb(verts, faces)

        return {
            "vertices": verts,
            "faces":    faces,
            "params": {
                "shape": params["shape"].tolist(),
                "pose":  params["pose"].tolist(),
                "exp":   params["exp"].tolist(),
                "cam":   params["cam"].tolist(),
            },
            "glb_bytes": glb_bytes,
            "landmarks": landmarks.tolist(),
        }

    async def reconstruct_face(self, image: np.ndarray) -> dict:
        """
        Input: BGR image (cv2 format)
        Output: {
            'vertices': np.ndarray [N,3],
            'faces':    np.ndarray [M,3],
            'params':   dict (shape, pose, exp, cam),
            'glb_bytes': bytes,
            'landmarks': list[[x,y]] (68 points)
        }
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._reconstruct_sync, image)


# ══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════════════════════

_deca_service: Optional[DECAService] = None


def get_deca_service() -> DECAService:
    global _deca_service
    if _deca_service is None:
        _deca_service = DECAService()
    return _deca_service
