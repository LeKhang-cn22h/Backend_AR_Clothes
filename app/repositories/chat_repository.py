from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from models.chat_session import ChatSession, ChatMessage


class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Sessions ────────────────────────────────────────────────
    async def create_session(self, user_id: int, title: str) -> ChatSession:
        session = ChatSession(user_id=user_id, title=title)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: int) -> ChatSession | None:
        result = await self.db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_sessions_by_user(self, user_id: int, skip: int = 0, limit: int = 20) -> list[ChatSession]:
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def update_session_title(self, session_id: int, title: str) -> ChatSession | None:
        session = await self.get_session(session_id)
        if not session:
            return None
        session.title = title
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def delete_session(self, session_id: int) -> None:
        await self.db.execute(delete(ChatSession).where(ChatSession.id == session_id))
        await self.db.commit()

    # ── Messages ────────────────────────────────────────────────
    async def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        suggested_products: str | None = None,
        image_url: str | None = None,
    ) -> ChatMessage:
        msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            suggested_products=suggested_products,
            image_url=image_url,
        )
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def get_messages(self, session_id: int) -> list[ChatMessage]:
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        return list(result.scalars().all())

    async def delete_message(self, message_id: int) -> None:
        await self.db.execute(delete(ChatMessage).where(ChatMessage.id == message_id))
        await self.db.commit()