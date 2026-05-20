# -*- coding: utf-8 -*-
"""FaceSwapService.

InsightFace (buffalo_l) phát hiện mặt + INSwapper (inswapper_128.onnx) hoán mặt.
DWpose (qua FitDiTService) đếm body keypoints để phân biệt full-body vs face-only.
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np
from PIL import Image

from config import settings


# Số keypoints body tối thiểu để coi là "full body".
# DWpose body có 18 điểm (BODY_18) — tay/chân/hông cần thấy đủ.
MIN_BODY_KEYPOINTS = 8


def _pil_to_bgr(image: Image.Image) -> np.ndarray:
    rgb = np.array(image.convert("RGB"))
    return rgb[:, :, ::-1].copy()


def _bgr_to_pil(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(arr[:, :, ::-1])


class FaceSwapService:
    _instance: "FaceSwapService | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load(self) -> None:
        if self._loaded:
            return

        from insightface.app import FaceAnalysis
        from insightface.model_zoo import get_model

        insightface_home = settings.INSIGHTFACE_HOME
        models_dir = os.path.join(insightface_home, "models")
        inswapper_path = os.path.join(models_dir, "inswapper_128.onnx")

        if not os.path.exists(inswapper_path):
            raise FileNotFoundError(
                f"Khong tim thay inswapper_128.onnx tai {inswapper_path}"
            )

        # FaceAnalysis tự tìm trong ~/.insightface/models/<name>
        self._face_app = FaceAnalysis(
            name="buffalo_l",
            root=insightface_home,
            providers=["CPUExecutionProvider"],
        )
        self._face_app.prepare(ctx_id=0, det_size=(640, 640))

        self._swapper = get_model(
            inswapper_path,
            providers=["CPUExecutionProvider"],
        )

        os.makedirs(settings.BODY_TEMPLATES_DIR, exist_ok=True)
        self._loaded = True
        print("[FaceSwap] InsightFace + inswapper loaded.")

    # ------------------------------------------------------------------
    # Face detection
    # ------------------------------------------------------------------
    def detect_faces(self, image: Image.Image) -> list:
        if not self._loaded:
            self.load()
        bgr = _pil_to_bgr(image)
        return self._face_app.get(bgr)

    def detect_face(self, image: Image.Image) -> bool:
        return len(self.detect_faces(image)) > 0

    # ------------------------------------------------------------------
    # Body detection (DWpose từ FitDiTService)
    # ------------------------------------------------------------------
    @staticmethod
    def _count_body_keypoints(dwpose_detector, image: Image.Image) -> int:
        """Đếm số body keypoints hợp lệ của người đầu tiên."""
        arr = np.array(image.convert("RGB"))[:, :, ::-1]
        _, _, _, candidate = dwpose_detector(arr)
        if candidate is None or len(candidate) == 0:
            return 0
        candidate = candidate[0]  # person 0
        # DWpose: 18 body + 2 foot + 21*2 hand + 68 face. Body nằm ở 18 phần tử đầu.
        body = candidate[:18] if len(candidate) >= 18 else candidate
        # Mỗi keypoint là (x, y) chuẩn hoá [0..1]; điểm không phát hiện = (-1, -1)
        # đã được clip về 0 trong fitdit.py — ở đây dùng ngưỡng > 0.
        valid = np.sum((body[:, 0] > 0) | (body[:, 1] > 0))
        return int(valid)

    def is_full_body(self, image: Image.Image, dwpose_detector) -> bool:
        return self._count_body_keypoints(dwpose_detector, image) >= MIN_BODY_KEYPOINTS

    def is_face_only(self, image: Image.Image, dwpose_detector) -> bool:
        # Có mặt nhưng không đủ body keypoints
        if not self.detect_face(image):
            return False
        return not self.is_full_body(image, dwpose_detector)

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------
    def get_body_template(self, gender: str = "neutral") -> Image.Image:
        gender = (gender or "neutral").lower()
        candidates = [
            f"{gender}_template.jpg",
            f"{gender}_template.png",
            "neutral_template.jpg",
            "male_template.jpg",
            "female_template.jpg",
        ]
        for name in candidates:
            path = os.path.join(settings.BODY_TEMPLATES_DIR, name)
            if os.path.exists(path):
                return Image.open(path).convert("RGB")
        raise FileNotFoundError(
            f"Khong tim thay body template trong {settings.BODY_TEMPLATES_DIR}"
        )

    # ------------------------------------------------------------------
    # Face swap
    # ------------------------------------------------------------------
    def swap_face(
        self,
        face_image: Image.Image,
        target_image: Image.Image,
    ) -> Image.Image:
        if not self._loaded:
            self.load()

        src_bgr = _pil_to_bgr(face_image)
        tgt_bgr = _pil_to_bgr(target_image)

        src_faces = self._face_app.get(src_bgr)
        if not src_faces:
            raise ValueError("Khong phat hien khuon mat trong anh nguon")
        # Mặt to nhất ở ảnh nguồn
        src_face = max(
            src_faces,
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
        )

        tgt_faces = self._face_app.get(tgt_bgr)
        if not tgt_faces:
            raise ValueError("Khong phat hien khuon mat trong anh template")
        tgt_face = max(
            tgt_faces,
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
        )

        out_bgr = self._swapper.get(
            tgt_bgr, tgt_face, src_face, paste_back=True
        )
        return _bgr_to_pil(out_bgr)
