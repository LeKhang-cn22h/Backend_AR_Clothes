from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:    Mapped[int]      = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title:      Mapped[str]      = mapped_column(String(255), nullable=False, default="Cuộc trò chuyện mới")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    messages: Mapped[list["ChatMessage"]] = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", lazy="selectin")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id:                  Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id:          Mapped[int]           = mapped_column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role:                Mapped[str]           = mapped_column(String(20), nullable=False)        # user | assistant
    content:             Mapped[str]           = mapped_column(Text, nullable=False)
    suggested_products:  Mapped[str | None]    = mapped_column(Text, nullable=True)               # JSON string
    image_url:           Mapped[str | None]    = mapped_column(String(500), nullable=True)        # ảnh user gửi
    created_at:          Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")