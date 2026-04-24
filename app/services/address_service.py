from fastapi import HTTPException
from models.address import Address
from repositories.address_repository import AddressRepository
from repositories.user_repository import UserRepository
from schemas.address import AddressCreate, AddressUpdate


class AddressService:
    def __init__(self, repo: AddressRepository, user_repo: UserRepository):
        self.repo = repo
        self.user_repo = user_repo

    async def create(self, user_id: int, data: AddressCreate) -> Address:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")
        if data.is_default:
            await self.repo.clear_default_for_user(user_id)
        return await self.repo.create(user_id, data)

    async def get_by_id(self, user_id: int, id: int) -> Address:
        address = await self.repo.get_by_id(id)
        if not address or address.user_id != user_id:
            raise HTTPException(status_code=404, detail="Khong tim thay dia chi")
        return address

    async def get_all_by_user(self, user_id: int) -> list[Address]:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")
        return await self.repo.get_all_by_user(user_id)

    async def update(self, user_id: int, id: int, data: AddressUpdate) -> Address:
        await self.get_by_id(user_id, id)
        if data.is_default:
            await self.repo.clear_default_for_user(user_id)
        updated = await self.repo.update(id, data)
        if not updated:
            raise HTTPException(status_code=404, detail="Khong tim thay dia chi")
        return updated

    async def delete(self, user_id: int, id: int) -> None:
        await self.get_by_id(user_id, id)
        await self.repo.delete(id)

    async def set_default(self, user_id: int, id: int) -> Address:
        await self.get_by_id(user_id, id)
        await self.repo.clear_default_for_user(user_id)
        updated = await self.repo.update(id, AddressUpdate(is_default=True))
        if not updated:
            raise HTTPException(status_code=404, detail="Khong tim thay dia chi")
        return updated
