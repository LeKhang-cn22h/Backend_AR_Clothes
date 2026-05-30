from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from repositories.address_repository import AddressRepository
from repositories.user_repository import UserRepository
from schemas.address import AddressCreate, AddressUpdate, AddressResponse
from services.address_service import AddressService
from core.limiter import limiter

router = APIRouter(prefix="/users/{user_id}/addresses", tags=["Addresses"])


def get_service(db: AsyncSession = Depends(get_db)) -> AddressService:
    return AddressService(AddressRepository(db), UserRepository(db))


@router.post("", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create(user_id: int, payload: AddressCreate, service: AddressService = Depends(get_service)):
    return await service.create(user_id, payload)


@router.get("", response_model=list[AddressResponse])
@limiter.limit("120/minute")
async def get_all(user_id: int, service: AddressService = Depends(get_service)):
    return await service.get_all_by_user(user_id)


@router.get("/{id}", response_model=AddressResponse)
@limiter.limit("120/minute")
async def get_one(user_id: int, id: int, service: AddressService = Depends(get_service)):
    return await service.get_by_id(user_id, id)


@router.put("/{id}", response_model=AddressResponse)
@limiter.limit("120/minute")
async def update(user_id: int, id: int, payload: AddressUpdate, service: AddressService = Depends(get_service)):
    return await service.update(user_id, id, payload)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("120/minute")
async def delete(user_id: int, id: int, service: AddressService = Depends(get_service)):
    await service.delete(user_id, id)


@router.patch("/{id}/set-default", response_model=AddressResponse)
@limiter.limit("120/minute")
async def set_default(user_id: int, id: int, service: AddressService = Depends(get_service)):
    return await service.set_default(user_id, id)
