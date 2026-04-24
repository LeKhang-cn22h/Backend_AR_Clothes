from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from repositories.user_repository import UserRepository
from schemas.user import UserCreate, UserUpdate, UserResponse
from services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


def get_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db))


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_or_upsert(payload: UserCreate, service: UserService = Depends(get_service)):
    return await service.upsert(payload)


@router.get("", response_model=list[UserResponse])
async def get_all(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: UserService = Depends(get_service),
):
    return await service.get_all(skip=skip, limit=limit)


@router.get("/by-uid/{firebase_uid}", response_model=UserResponse)
async def get_by_uid(firebase_uid: str, service: UserService = Depends(get_service)):
    return await service.get_by_firebase_uid(firebase_uid)


@router.get("/{id}", response_model=UserResponse)
async def get_one(id: int, service: UserService = Depends(get_service)):
    return await service.get_by_id(id)


@router.patch("/{id}", response_model=UserResponse)
async def update(id: int, payload: UserUpdate, service: UserService = Depends(get_service)):
    return await service.update(id, payload)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(id: int, service: UserService = Depends(get_service)):
    await service.delete(id)
