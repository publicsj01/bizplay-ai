# SQLAlchemy ORM 엔티티 — Spring AI JPA Entity 1:1 대응
# Spring AI: @Entity + @Table → SQLAlchemy DeclarativeBase

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional


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


# ── Corp 테넌트 계층 ──────────────────────────────────────────────────────────
# Spring AI: CorpGroup.java + Corporation.java 1:1 대응
# 구조: CorpGroup (최상위) → Corporation (corp_no 소유) → Bot (soft ref)

class CorpGroup(Base):
    """
    법인 그룹. 관련 Corporation 행들을 묶는 최상위 단위.
    Spring AI: CorpGroup.java (corp_group 테이블)
    """
    __tablename__ = "corp_group"

    id: Mapped[int] = mapped_column("corp_group_id", BigInteger, primary_key=True, autoincrement=True)
    corp_group_cd: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)


class Corporation(Base):
    """
    법인. corp_no가 자연 비즈니스 식별자(UNIQUE).
    Bot.corp_no는 이 테이블을 soft ref(FK 없음)로 참조.
    Spring AI: Corporation.java (corp 테이블)
    """
    __tablename__ = "corp"

    id: Mapped[int] = mapped_column("corp_id", BigInteger, primary_key=True, autoincrement=True)
    corp_no: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    corp_group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("corp_group.corp_group_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    corp_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Spring AI: @CreatedDate → Spring Data Auditing. 여기서는 서버 기본값 사용
    created_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Bot(Base):
    __tablename__ = "bots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    corp_no: Mapped[str] = mapped_column(String(50), nullable=False, default="DEFAULT")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_expose: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    llm_model: Mapped[str] = mapped_column(String(255), nullable=False)
    llm_temperature: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False, default=Decimal("0.0"))
    max_answer_length: Mapped[int] = mapped_column(Integer, nullable=False, default=2048)
    history_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Telegram 연동 (Spring AI: Bot.java telegram_* 필드)
    telegram_bot_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telegram_bot_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telegram_last_offset: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    telegram_configured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Kakao 연동
    kakao_webhook_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    kakao_bot_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    kakao_configured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    documents: Mapped[List["Document"]] = relationship("Document", back_populates="bot", cascade="all, delete-orphan")
    chat_sessions: Mapped[List["ChatSession"]] = relationship(
        "ChatSession", back_populates="bot", cascade="all, delete-orphan"
    )
    recommended_questions: Mapped[List["BotRecommendedQuestion"]] = relationship(
        "BotRecommendedQuestion", back_populates="bot", cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
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
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at.asc()",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    lang: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    # 토큰 수는 assistant 메시지에만 기록 (Spring AI: ChatMessage.java 동일)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")


class BotRecommendedQuestion(Base):
    __tablename__ = "bot_recommended_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(Text, nullable=False)

    bot: Mapped["Bot"] = relationship("Bot", back_populates="recommended_questions")
