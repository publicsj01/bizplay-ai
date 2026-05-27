# 채팅 라우터 — Spring AI ChatController.java 1:1 대응
# POST /api/v1/rag/chat
# GET  /api/v1/rag/chat/models
# GET  /api/v1/rag/chat/history/{session_id}

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.entities import ChatSession
from app.models.schemas import (
    ApiResponse,
    ChatHistoryMessage,
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
    LlmModelInfo,
)
from app.services.chat import handle_chat
from app.services.llm import list_available_models

router = APIRouter(prefix="/api/v1/rag/chat", tags=["chat"])


@router.post("", response_model=ApiResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)) -> ApiResponse:
    """Spring AI: ChatController.chat() 대응"""
    result = await handle_chat(db, req)
    return ApiResponse(success=True, data=result.model_dump())


@router.get("/models", response_model=ApiResponse)
async def get_models() -> ApiResponse:
    """Spring AI: ChatController.getModels() 대응"""
    models = list_available_models()
    return ApiResponse(success=True, data=[LlmModelInfo(**m).model_dump() for m in models])


@router.get("/history/{session_id}", response_model=ApiResponse)
async def get_history(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """Spring AI: ChatController.getHistory() 대응"""
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        return ApiResponse(success=False, error="Session not found")

    data = ChatSessionResponse(
        id=session.id,
        bot_id=session.bot_id,
        channel=session.channel,
        created_at=session.created_at,
        messages=[
            ChatHistoryMessage(
                id=m.id,
                role=m.role,
                content=m.content,
                lang=m.lang,
                created_at=m.created_at,
            )
            for m in session.messages
        ],
    )
    return ApiResponse(success=True, data=data.model_dump())
