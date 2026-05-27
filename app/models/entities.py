# SQLAlchemy ORM 엔티티 — Spring AI JPA Entity 1:1 대응
# Spring AI: @Entity + @Table → SQLAlchemy DeclarativeBase

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Bot(Base):
    __tablename__ = "bots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    corp_no: Mapped[str] = mapped_column(String(50), nullable=False, default="DEFAULT")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_expose: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    llm_model: Mapped[str] = mapped_column(String(255), nullable=False)
    llm_temperature: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False, default=Decimal("0.0"))
    max_answer_length: Mapped[int] = mapped_column(Integer, nullable=False, default=2048)
    history_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Telegram 연동 (Spring AI: Bot.java telegram_* 필드)
    telegram_bot_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_bot_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_last_offset: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    telegram_configured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Kakao 연동
    kakao_webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kakao_bot_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kakao_configured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    documents: Mapped[list["Document"]] = relationship("Document", back_populates="bot", cascade="all, delete-orphan")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        "ChatSession", back_populates="bot", cascade="all, delete-orphan"
    )
    recommended_questions: Mapped[list["BotRecommendedQuestion"]] = relationship(
        "BotRecommendedQuestion", back_populates="bot", cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Spring AI: EmbeddingStatus enum (PENDING/PROCESSING/COMPLETED/FAILED)
    embedding_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    bot: Mapped["Bot"] = relationship("Bot", back_populates="documents")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"))
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="web")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bot: Mapped["Bot"] = relationship("Bot", back_populates="chat_sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        # Spring AI: createdAt ASC, role DESC 정렬과 동일
        order_by="ChatMessage.created_at.asc()",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    lang: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # 토큰 수는 assistant 메시지에만 기록 (Spring AI: ChatMessage.java 동일)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")


class BotRecommendedQuestion(Base):
    __tablename__ = "bot_recommended_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(Text, nullable=False)

    bot: Mapped["Bot"] = relationship("Bot", back_populates="recommended_questions")
