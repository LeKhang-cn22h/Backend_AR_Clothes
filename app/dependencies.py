# -*- coding: utf-8 -*-
from services.fitdit import FitDiTService
from services.face_swap_service import FaceSwapService

_fitdit: FitDiTService | None = None
_face_swap: FaceSwapService | None = None


def get_fitdit_service() -> FitDiTService:
    return _fitdit


def get_face_swap_service() -> FaceSwapService:
    return _face_swap


def init_service():
    global _fitdit, _face_swap
    _fitdit = FitDiTService()
    _fitdit.load()
    _face_swap = FaceSwapService()
    _face_swap.load()
