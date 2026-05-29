# Pydantic 스키마 — Spring AI DTO 1:1 대응
# Spring AI: @RequestBody DTO / @ResponseBody DTO → Pydantic BaseModel

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── 공통 응답 래퍼 (Spring AI: ApiResponse<T>) ──────────────────────────────

class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[str] = None


# ── Bot ───────────────────────────────────────────────────────────────────────

class RecommendedQuestionDto(BaseModel):
    question: str


class BotCreateRequest(BaseModel):
    corp_no: Optional[str] = Field(default=None, max_length=50)
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    system_prompt: Optional[str] = None
    source_expose: bool = True
    llm_model: str = Field(..., min_length=1)
    llm_temperature: Decimal = Field(default=Decimal("0.0"), ge=0, le=1)
    max_answer_length: int = Field(default=2048, ge=64, le=8192)
    history_turns: int = Field(default=5, ge=0, le=20)
    top_k: int = Field(default=5, ge=1, le=50)
    recommended_questions: List[RecommendedQuestionDto] = Field(default_factory=list)


class BotUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    system_prompt: Optional[str] = None
    source_expose: Optional[bool] = None
    llm_model: Optional[str] = None
    llm_temperature: Optional[Decimal] = Field(default=None, ge=0, le=1)
    max_answer_length: Optional[int] = Field(default=None, ge=64, le=8192)
    history_turns: Optional[int] = Field(default=None, ge=0, le=20)
    top_k: Optional[int] = Field(default=None, ge=1, le=50)
    recommended_questions: Optional[List[RecommendedQuestionDto]] = None


class BotResponse(BaseModel):
    id: uuid.UUID
    corp_no: str
    name: str
    description: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    system_prompt: Optional[str]
    source_expose: bool
    llm_model: str
    llm_temperature: Decimal
    max_answer_length: int
    history_turns: int
    top_k: int
    disabled: bool
    telegram_configured: bool
    telegram_bot_username: Optional[str]
    telegram_configured_at: Optional[datetime]
    kakao_configured: bool
    kakao_bot_name: Optional[str]
    kakao_configured_at: Optional[datetime]
    recommended_questions: List[RecommendedQuestionDto]
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
    content_type: Optional[str]
    embedding_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    bot_id: uuid.UUID
    query: str = Field(..., min_length=1)
    session_id: Optional[uuid.UUID] = None
    channel: Optional[str] = Field(default="web", max_length=20)


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
    sources: List[ChatSource] = Field(default_factory=list)


class ChatHistoryMessage(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    lang: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    id: uuid.UUID
    bot_id: uuid.UUID
    channel: str
    created_at: datetime
    messages: List[ChatHistoryMessage] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ── LLM 모델 목록 ─────────────────────────────────────────────────────────────

class LlmModelInfo(BaseModel):
    name: str
    label: str
    model: str


# ── CorpGroup ──────────────────────────────────────────────────────────────────
# Spring AI: CorpGroupCreateRequest / CorpGroupResponse / CorpGroupUpdateRequest

class CorpGroupCreateRequest(BaseModel):
    corp_group_cd: str = Field(..., min_length=1, max_length=20)


class CorpGroupUpdateRequest(BaseModel):
    corp_group_cd: Optional[str] = Field(default=None, max_length=20)


class CorpGroupResponse(BaseModel):
    id: int
    corp_group_cd: str

    model_config = {"from_attributes": True}


# ── Corporation ────────────────────────────────────────────────────────────────
# Spring AI: CorpCreateRequest / CorpResponse / CorpUpdateRequest

class CorpCreateRequest(BaseModel):
    corp_no: str = Field(..., min_length=1, max_length=50)
    corp_group_id: int
    corp_name: str = Field(..., min_length=1, max_length=255)


class CorpUpdateRequest(BaseModel):
    # corp_no는 변경 불가 (경로 식별자) — Spring AI: CorpUpdateRequest.java 동일
    corp_group_id: Optional[int] = None
    corp_name: Optional[str] = Field(default=None, max_length=255)


class CorpResponse(BaseModel):
    id: int
    corp_no: str
    corp_group_id: int
    corp_name: str
    created_date: datetime

    model_config = {"from_attributes": True}
