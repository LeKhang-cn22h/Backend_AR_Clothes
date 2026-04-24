from fastapi import HTTPException
from models.user import User
from repositories.user_repository import UserRepository
from schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def upsert(self, data: UserCreate) -> User:
        existing = await self.repo.get_by_firebase_uid(data.firebase_uid)
        if existing:
            update_data = UserUpdate(
                email=data.email,
                display_name=data.display_name,
                phone=data.phone,
                avatar_url=data.avatar_url,
            )
            return await self.repo.update(existing.id, update_data)
        email_user = await self.repo.get_by_email(str(data.email))
        if email_user:
            raise HTTPException(status_code=409, detail="Email da duoc su dung")
        return await self.repo.create(data)

    async def get_by_id(self, id: int) -> User:
        user = await self.repo.get_by_id(id)
        if not user:
            raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")
        return user

    async def get_by_firebase_uid(self, firebase_uid: str) -> User:
        user = await self.repo.get_by_firebase_uid(firebase_uid)
        if not user:
            raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")
        return user

    async def get_all(self, skip: int = 0, limit: int = 20) -> list[User]:
        return await self.repo.get_all(skip=skip, limit=limit)

    async def update(self, id: int, data: UserUpdate) -> User:
        if data.email:
            existing = await self.repo.get_by_email(str(data.email))
            if existing and existing.id != id:
                raise HTTPException(status_code=409, detail="Email da duoc su dung")
        user = await self.repo.update(id, data)
        if not user:
            raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")
        return user

    async def delete(self, id: int) -> None:
        deleted = await self.repo.delete(id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")
