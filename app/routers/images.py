# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Query

import services.cloudinary_service as cloud

router = APIRouter(prefix="/images", tags=["images"])

DEFAULT_FOLDER = "tryon_results"


@router.get("")
def list_images(
    folder: str = Query(default=DEFAULT_FOLDER),
    max_results: int = Query(default=50, ge=1, le=500),
):
    try:
        return cloud.list_images(folder=folder, max_results=max_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Loi lay danh sach anh: {e}")


@router.get("/{public_id:path}")
def get_image(public_id: str):
    try:
        return cloud.get_image(public_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Khong tim thay anh: {e}")


@router.delete("")
def delete_all_images(folder: str = Query(default=DEFAULT_FOLDER)):
    try:
        return cloud.delete_all_images(folder=folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Loi xoa tat ca anh: {e}")


@router.delete("/{public_id:path}")
def delete_image(public_id: str):
    try:
        return cloud.delete_image(public_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Loi xoa anh: {e}")
