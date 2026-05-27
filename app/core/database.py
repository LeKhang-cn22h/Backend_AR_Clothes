# -*- coding: utf-8 -*-
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from config import settings
from sqlalchemy import text


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
    from models.user import User  # noqa: F401
    from models.store import Store  # noqa: F401
    from models.garment_category import GarmentCategory  # noqa: F401
    from models.garment import Garment  # noqa: F401
    from models.address import Address  # noqa: F401
    from models.review import Review  # noqa: F401
    from models.body_profile import BodyProfile  # noqa: F401
    from models.chat_session import ChatSession, ChatMessage      # noqa
    from models.product_embedding import ProductEmbedding  
    from models.garment_size_spec import GarmentSizeSpec  
    from models.tryon_history import TryonHistory  
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)