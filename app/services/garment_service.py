import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from config import settings
from models.garment import Garment
from schemas.garment import GarmentCreate, GarmentUpdate
from core.cloudinary import cloudinary

LENS_ID = "8db6dfc4-c7f3-4cc6-a7d5-d4e335db567f"
GLB_FOLDER = "ar_garments"



def _upload_glb(file: UploadFile) -> dict:
    if not file.filename.endswith(".glb"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .glb")

    result = cloudinary.uploader.upload(
        file.file,
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


async def create_garment(
    db: AsyncSession,
    data: GarmentCreate,
    file: UploadFile,
) -> Garment:
    uploaded = _upload_glb(file)

    garment = Garment(
        name=data.name,
        description=data.description,
        item_index=data.item_index,
        category_id=data.category_id,
        store_id=data.store_id,
        model_url=uploaded["url"],
        public_id=uploaded["public_id"],
    )
    db.add(garment)
    await db.commit()
    await db.refresh(garment)
    return garment


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

    if file:
        _delete_glb(garment.public_id)
        uploaded = _upload_glb(file)
        garment.model_url = uploaded["url"]
        garment.public_id = uploaded["public_id"]

    await db.commit()
    await db.refresh(garment)
    return garment


async def delete_garment(db: AsyncSession, garment_id: int) -> dict:
    garment = await get_garment_by_id(db, garment_id)
    _delete_glb(garment.public_id)
    await db.execute(delete(Garment).where(Garment.id == garment_id))
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
