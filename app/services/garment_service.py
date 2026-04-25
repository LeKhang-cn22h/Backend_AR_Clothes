import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from models.garment import Garment
from schemas.garment import GarmentCreate, GarmentUpdate
from core.cloudinary import cloudinary

LENS_ID = "8db6dfc4-c7f3-4cc6-a7d5-d4e335db567f"
GLB_FOLDER = "ar_garments"
CLOTH_IMAGE_FOLDER = "ar_garments_cloth"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _upload_glb(file: UploadFile) -> dict:
    filename = file.filename or ""
    if filename and not filename.endswith(".glb"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .glb")

    # Reset con trỏ về đầu rồi đọc bytes
    file.file.seek(0)
    contents = file.file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="File GLB rỗng")

    result = cloudinary.uploader.upload(
        contents,          # <-- truyền bytes thay vì file object
        folder=GLB_FOLDER,
        resource_type="raw",
        use_filename=True,
        unique_filename=True,
        format="glb",
    )
    return {
        "url": result["secure_url"],
        "public_id": result["public_id"],
    }

def _delete_glb(public_id: str):
    cloudinary.uploader.destroy(public_id, resource_type="raw")


def _upload_cloth_image(file: UploadFile) -> dict:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Cloth image phải là image/jpeg, image/png hoặc image/webp",
        )
    result = cloudinary.uploader.upload(
        file.file,
        folder=CLOTH_IMAGE_FOLDER,
        resource_type="image",
        use_filename=True,
        unique_filename=True,
    )
    return {"url": result["secure_url"], "public_id": result["public_id"]}


async def create_garment(
    db: AsyncSession,
    data: GarmentCreate,
    file: UploadFile,
    cloth_image: UploadFile | None = None,
) -> Garment:
    uploaded = _upload_glb(file)

    cloth_uploaded = _upload_cloth_image(cloth_image) if cloth_image else None

    garment = Garment(
        name=data.name,
        description=data.description,
        item_index=data.item_index,
        category_id=data.category_id,
        store_id=data.store_id,
        firestore_product_id=data.firestore_product_id,
        color=data.color,
        model_url=uploaded["url"],
        public_id=uploaded["public_id"],
        cloth_image_url=cloth_uploaded["url"] if cloth_uploaded else None,
        cloth_image_public_id=cloth_uploaded["public_id"] if cloth_uploaded else None,
    )
    db.add(garment)
    await db.commit()
    await db.refresh(garment)
    return garment


async def get_garments_by_firestore_id(
    db: AsyncSession,
    firestore_product_id: str,
) -> list[Garment]:
    """Trả về TẤT CẢ garments theo firestore_product_id (nhiều màu)"""
    result = await db.execute(
        select(Garment).where(
            Garment.firestore_product_id == firestore_product_id,
            Garment.is_deleted == False,
        ).order_by(Garment.id)
    )
    return result.scalars().all()


async def get_all_garments(db: AsyncSession) -> list[Garment]:
    result = await db.execute(select(Garment).order_by(Garment.id))
    return result.scalars().all()


async def get_garment_by_id(db: AsyncSession, garment_id: int) -> Garment:
    result = await db.execute(select(Garment).where(Garment.id == garment_id))
    garment = result.scalar_one_or_none()
    if not garment:
        raise HTTPException(status_code=404, detail="Không tìm thấy garment")
    return garment


async def update_garment(
    db: AsyncSession,
    garment_id: int,
    data: GarmentUpdate,
    file: UploadFile | None = None,
    cloth_image: UploadFile | None = None,
) -> Garment:
    garment = await get_garment_by_id(db, garment_id)

    if data.name is not None:
        garment.name = data.name
    if data.description is not None:
        garment.description = data.description
    if data.item_index is not None:
        garment.item_index = data.item_index
    if data.category_id is not None:
        garment.category_id = data.category_id
    if data.store_id is not None:
        garment.store_id = data.store_id
    if data.firestore_product_id is not None:
        garment.firestore_product_id = data.firestore_product_id
    if data.color is not None:
        garment.color = data.color

    if file:
        _delete_glb(garment.public_id)
        uploaded = _upload_glb(file)
        garment.model_url = uploaded["url"]
        garment.public_id = uploaded["public_id"]

    if cloth_image:
        if garment.cloth_image_public_id:
            cloudinary.uploader.destroy(garment.cloth_image_public_id, resource_type="image")
        cloth_uploaded = _upload_cloth_image(cloth_image)
        garment.cloth_image_url = cloth_uploaded["url"]
        garment.cloth_image_public_id = cloth_uploaded["public_id"]

    await db.commit()
    await db.refresh(garment)
    return garment


async def delete_garment(db: AsyncSession, garment_id: int) -> dict:
    garment = await get_garment_by_id(db, garment_id)

    if garment.public_id:
        _delete_glb(garment.public_id)

    if garment.cloth_image_public_id:
        cloudinary.uploader.destroy(garment.cloth_image_public_id, resource_type="image")

    garment.is_deleted = True
    await db.commit()
    return {"deleted": garment_id}


async def get_lens_link(db: AsyncSession, garment_id: int) -> dict:
    garment = await get_garment_by_id(db, garment_id)
    lens_url = (
        f"https://www.snapchat.com/lens/{LENS_ID}"
        f"?model_url={garment.model_url}"
        f"&product_id={garment.id}"
    )
    return {
        "lens_url": lens_url,
        "model_url": garment.model_url,
        "product_id": garment.id,
    }
