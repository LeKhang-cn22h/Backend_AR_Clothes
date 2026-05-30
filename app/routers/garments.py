import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.garment import GarmentCreate, GarmentUpdate, GarmentResponse, LensLinkResponse
import services.garment_service as svc
from core.limiter import limiter

router = APIRouter(prefix="/garments", tags=["Garments"])


@router.post("/", response_model=GarmentResponse, status_code=201)
@limiter.limit("20/minute")
async def create(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    item_index: Optional[int] = Form(None),
    category_id: Optional[int] = Form(None),
    store_id: Optional[uuid.UUID] = Form(None),
    firestore_product_id: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    cloth_image: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    data = GarmentCreate(
        name=name,
        description=description,
        item_index=item_index,
        category_id=category_id,
        store_id=store_id,
        firestore_product_id=firestore_product_id,
        color=color,
    )
    return await svc.create_garment(db, data, cloth_image)


@router.get("/", response_model=list[GarmentResponse])
@limiter.limit("120/minute")
async def get_all(db: AsyncSession = Depends(get_db)):
    return await svc.get_all_garments(db)


@router.get("/by-product/{firestore_product_id}", response_model=list[GarmentResponse])
@limiter.limit("120/minute")
async def get_by_firestore_product(
    firestore_product_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy TẤT CẢ garments theo Firebase product ID.
    Mỗi garment = 1 màu của sản phẩm.
    Trả về list rỗng nếu không tìm thấy (không raise 404).
    """
    return await svc.get_garments_by_firestore_id(db, firestore_product_id)


@router.get("/{garment_id}", response_model=GarmentResponse)
@limiter.limit("120/minute")
async def get_one(garment_id: int, db: AsyncSession = Depends(get_db)):
    return await svc.get_garment_by_id(db, garment_id)


@router.put("/{garment_id}", response_model=GarmentResponse)
@limiter.limit("20/minute")
async def update(
    garment_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    item_index: Optional[int] = Form(None),
    category_id: Optional[int] = Form(None),
    store_id: Optional[uuid.UUID] = Form(None),
    firestore_product_id: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    cloth_image: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    data = GarmentUpdate(
        name=name,
        description=description,
        item_index=item_index,
        category_id=category_id,
        store_id=store_id,
        firestore_product_id=firestore_product_id,
        color=color,
    )
    return await svc.update_garment(db, garment_id, data, cloth_image)


@router.delete("/{garment_id}")
@limiter.limit("20/minute")
async def delete(garment_id: int, db: AsyncSession = Depends(get_db)):
    return await svc.delete_garment(db, garment_id)


@router.get("/{garment_id}/lens-link", response_model=LensLinkResponse)
@limiter.limit("120/minute")
async def lens_link(garment_id: int, db: AsyncSession = Depends(get_db)):
    return await svc.get_lens_link(db, garment_id)