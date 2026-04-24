# -*- coding: utf-8 -*-
import io
from datetime import datetime, timezone
from typing import Optional

import cloudinary
import cloudinary.uploader
import cloudinary.api
from PIL import Image

from config import settings
from core.cloudinary import cloudinary

DEFAULT_FOLDER = "tryon_results"


def upload_image(
    pil_image: Image.Image,
    folder: str = DEFAULT_FOLDER,
    public_id: Optional[str] = None,
) -> dict:
    buf = io.BytesIO()
    pil_image.save(buf, format="JPEG")
    buf.seek(0)

    kwargs = {"folder": folder, "resource_type": "image"}
    if public_id:
        kwargs["public_id"] = public_id

    result = cloudinary.uploader.upload(buf, **kwargs)
    return {
        "url": result["secure_url"],
        "public_id": result["public_id"],
        "created_at": result.get("created_at", datetime.now(timezone.utc).isoformat()),
    }


def get_image(public_id: str) -> dict:
    result = cloudinary.api.resource(public_id, resource_type="image")
    return {
        "url": result["secure_url"],
        "public_id": result["public_id"],
        "width": result.get("width"),
        "height": result.get("height"),
        "created_at": result.get("created_at"),
    }


def list_images(folder: str = DEFAULT_FOLDER, max_results: int = 50) -> list:
    result = cloudinary.api.resources(
        type="upload",
        prefix=folder + "/",
        max_results=max_results,
        resource_type="image",
    )
    return [
        {
            "url": r["secure_url"],
            "public_id": r["public_id"],
            "width": r.get("width"),
            "height": r.get("height"),
            "created_at": r.get("created_at"),
        }
        for r in result.get("resources", [])
    ]


def delete_image(public_id: str) -> dict:
    result = cloudinary.uploader.destroy(public_id, resource_type="image")
    return {"public_id": public_id, "result": result.get("result")}


def delete_all_images(folder: str = DEFAULT_FOLDER) -> dict:
    result = cloudinary.api.delete_resources_by_prefix(
        folder + "/", resource_type="image"
    )
    deleted = list(result.get("deleted", {}).keys())
    return {"deleted_count": len(deleted), "deleted": deleted}
