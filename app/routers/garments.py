# -*- coding: utf-8 -*-
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.garment import GarmentCreate, GarmentUpdate, GarmentResponse, LensLinkResponse
import services.garment_service as svc

router = APIRouter(prefix="/garments", tags=["Garments"])


@router.post("/", response_model=GarmentResponse, status_code=201)
async def create(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    item_index: Optional[int] = Form(None),
    category_id: Optional[int] = Form(None),
    firestore_product_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    data = GarmentCreate(
        name=name,
        description=description,
        item_index=item_index,
        category_id=category_id,
        firestore_product_id=firestore_product_id,
    )
    return await svc.create_garment(db, data, file)


@router.get("/", response_model=list[GarmentResponse])
async def get_all(db: AsyncSession = Depends(get_db)):
    return await svc.get_all_garments(db)


@router.get("/{garment_id}", response_model=GarmentResponse)
async def get_one(garment_id: int, db: AsyncSession = Depends(get_db)):
    return await svc.get_garment_by_id(db, garment_id)


@router.put("/{garment_id}", response_model=GarmentResponse)
async def update(
    garment_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    item_index: Optional[int] = Form(None),
    category_id: Optional[int] = Form(None),
    firestore_product_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    data = GarmentUpdate(
        name=name,
        description=description,
        item_index=item_index,
        category_id=category_id,
        firestore_product_id=firestore_product_id,
    )
    return await svc.update_garment(db, garment_id, data, file)


@router.delete("/{garment_id}")
async def delete(garment_id: int, db: AsyncSession = Depends(get_db)):
    return await svc.delete_garment(db, garment_id)


@router.get("/{garment_id}/lens-link", response_model=LensLinkResponse)
async def lens_link(garment_id: int, db: AsyncSession = Depends(get_db)):
    return await svc.get_lens_link(db, garment_id)