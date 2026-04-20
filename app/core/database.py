# -*- coding: utf-8 -*-
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from config import settings


def _build_async_url(url: str) -> str:
    url = url.replace("postgresql://", "postgresql+asyncpg://")
    for param in ["sslmode=require", "channel_binding=require", "sslmode=prefer"]:
        url = url.replace("&" + param, "").replace(param + "&", "").replace(param, "")
    return url.rstrip("?&")


engine = create_async_engine(
    _build_async_url(settings.DATABASE_URL),
    echo=False,
    pool_pre_ping=True,
    connect_args={"ssl": "require"},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)