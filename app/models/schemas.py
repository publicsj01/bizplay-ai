# Pydantic 스키마 — Spring AI DTO 1:1 대응
# Spring AI: @RequestBody DTO / @ResponseBody DTO → Pydantic BaseModel

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── 공통 응답 래퍼 (Spring AI: ApiResponse<T>) ──────────────────────────────

class ApiResponse(BaseModel):
    success: bool
    data: Any | None = None
    message: str | None = None
    error: str | None = None


# ── Bot ───────────────────────────────────────────────────────────────────────

class RecommendedQuestionDto(BaseModel):
    question: str


class BotCreateRequest(BaseModel):
    corp_no: str | None = Field(default=None, max_length=50)
    name: str = Field(..., min_length=1)
    description: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    system_prompt: str | None = None
    source_expose: bool = True
    llm_model: str = Field(..., min_length=1)
    llm_temperature: Decimal = Field(default=Decimal("0.0"), ge=0, le=1)
    max_answer_length: int = Field(default=2048, ge=64, le=8192)
    history_turns: int = Field(default=5, ge=0, le=20)
    top_k: int = Field(default=5, ge=1, le=50)
    recommended_questions: list[RecommendedQuestionDto] = Field(default_factory=list)


class BotUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    system_prompt: str | None = None
    source_expose: bool | None = None
    llm_model: str | None = None
    llm_temperature: Decimal | None = Field(default=None, ge=0, le=1)
    max_answer_length: int | None = Field(default=None, ge=64, le=8192)
    history_turns: int | None = Field(default=None, ge=0, le=20)
    top_k: int | None = Field(default=None, ge=1, le=50)
    recommended_questions: list[RecommendedQuestionDto] | None = None


class BotResponse(BaseModel):
    id: uuid.UUID
    corp_no: str
    name: str
    description: str | None
    contact_email: str | None
    contact_phone: str | None
    system_prompt: str | None
    source_expose: bool
    llm_model: str
    llm_temperature: Decimal
    max_answer_length: int
    history_turns: int
    top_k: int
    disabled: bool
    telegram_configured: bool
    telegram_bot_username: str | None
    telegram_configured_at: datetime | None
    kakao_configured: bool
    kakao_bot_name: str | None
    kakao_configured_at: datetime | None
    recommended_questions: list[RecommendedQuestionDto]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BotStatisticsResponse(BaseModel):
    bot_id: uuid.UUID
    document_count: int
    session_count: int
    message_count: int
    total_input_tokens: int
    total_output_tokens: int


class DailyStatisticsItem(BaseModel):
    date: str
    session_count: int
    message_count: int


class KeywordItem(BaseModel):
    keyword: str
    count: int


# ── Document ──────────────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: uuid.UUID
    bot_id: uuid.UUID
    title: str
    file_name: str
    content_type: str | None
    embedding_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    bot_id: uuid.UUID
    query: str = Field(..., min_length=1)
    session_id: uuid.UUID | None = None
    channel: str | None = Field(default="web", max_length=20)


class ChatSource(BaseModel):
    doc_id: str
    title: str
    file_name: str
    snippet: str  # 최대 300자 (Spring AI: ChatSource.java snippet field)
    score: float
    chunk_index: int
    document_url: str


class ChatResponse(BaseModel):
    answer: str
    session_id: uuid.UUID
    sources: list[ChatSource] = Field(default_factory=list)


class ChatHistoryMessage(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    lang: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    id: uuid.UUID
    bot_id: uuid.UUID
    channel: str
    created_at: datetime
    messages: list[ChatHistoryMessage] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ── LLM 모델 목록 ─────────────────────────────────────────────────────────────

class LlmModelInfo(BaseModel):
    name: str
    label: str
    model: str
