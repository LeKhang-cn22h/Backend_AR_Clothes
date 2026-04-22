import os
import shutil
import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from config import settings
from models.garment import Garment
from schemas.garment import GarmentCreate, GarmentUpdate

LENS_ID = "YOUR_LENS_ID"   
GLB_FOLDER = "ar_garments"

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
)


def _upload_glb(file: UploadFile) -> dict:
    """Upload file .glb lên Cloudinary, trả về url + public_id."""
    if not file.filename.endswith(".glb"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .glb")

    result = cloudinary.uploader.upload(
        file.file,
        folder=GLB_FOLDER,
        resource_type="raw",   # .glb không phải image → dùng raw
        use_filename=True,
        unique_filename=True,
        format="glb",
    )
    return {
        "url": result["secure_url"],
        "public_id": result["public_id"],
    }

def _save_glb_local(file:UploadFile,filename:str)->str:
    "Lưu file .glb vào thư mục local, trả về đường dẫn file"
    os.makedirs(settings.GLB_STATIC_DIR,exist_ok=True)
    safe_name= filename.replace(" ", "_")
    dest_path=os.path.join(settings.GLB_STATIC_DIR,safe_name)
    file.file.seek(0)
    with open(dest_path,"wb") as f:
        shutil.copyfileobj(file.file,f)
    
    return f"{settings.BASE_URL}/static/models/{safe_name}"

def _delete_glb(public_id: str):
    cloudinary.uploader.destroy(public_id, resource_type="raw")

def _delete_glb_local(file_name:str):
    "xóa file .glb trên local dựa vào name"
    path =os.path.join(settings.GLB_STATIC_DIR, file_name)
    if os.path.exists(path):
        os.remove(path)

# ── CREATE ────────────────────────────────────────────────────────────────────

async def create_garment(
    db: AsyncSession,
    data: GarmentCreate,
    file: UploadFile,
) -> Garment:
    uploaded = _upload_glb(file)
    local_url=_save_glb_local(file,file.filename)

    garment = Garment(
        name=data.name,
        description=data.description,
        item_index=data.item_index,
        model_url=uploaded["url"],
        local_url=local_url,
        public_id=uploaded["public_id"],
    )
    db.add(garment)
    await db.commit()
    await db.refresh(garment)
    return garment


# ── READ ──────────────────────────────────────────────────────────────────────

async def get_all_garments(db: AsyncSession) -> list[Garment]:
    result = await db.execute(select(Garment).order_by(Garment.id))
    return result.scalars().all()


async def get_garment_by_id(db: AsyncSession, garment_id: int) -> Garment:
    result = await db.execute(select(Garment).where(Garment.id == garment_id))
    garment = result.scalar_one_or_none()
    if not garment:
        raise HTTPException(status_code=404, detail="Không tìm thấy garment")
    return garment


# ── UPDATE ────────────────────────────────────────────────────────────────────

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

    # Nếu có file mới → xóa file cũ trên Cloudinary rồi upload mới
    if file:
        # Xóa file cũ
        _delete_glb(garment.public_id)
        if garment.local_url:
            old_filename = garment.local_url.split("/")[-1]
            _delete_glb_local(old_filename)

        # Upload file mới
        uploaded = _upload_glb(file)
        local_url = _save_glb_local(file, file.filename)

        garment.model_url = uploaded["url"]
        garment.public_id = uploaded["public_id"]
        garment.local_url = local_url

    await db.commit()
    await db.refresh(garment)
    return garment


# ── DELETE ────────────────────────────────────────────────────────────────────

async def delete_garment(db: AsyncSession, garment_id: int) -> dict:
    garment = await get_garment_by_id(db, garment_id)
    _delete_glb(garment.public_id)
    await db.execute(delete(Garment).where(Garment.id == garment_id))
    await db.commit()
    return {"deleted": garment_id}


# ── DEEP LINK ─────────────────────────────────────────────────────────────────

async def get_lens_link(db: AsyncSession, garment_id: int) -> dict:
    garment = await get_garment_by_id(db, garment_id)
    model_url=garment.local_url or garment.model_url
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