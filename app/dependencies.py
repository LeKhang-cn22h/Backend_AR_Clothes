# -*- coding: utf-8 -*-
from services.catvton import CatVTONService

_service: CatVTONService | None = None


def get_catvton_service() -> CatVTONService:
    return _service


def init_service():
    global _service
    _service = CatVTONService()
    _service.load()
