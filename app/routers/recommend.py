# 추천 질문 라우터 — Spring AI BotController.recommendedQuestions 대응
# GET /api/v1/bots/{bot_id}/recommend

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.entities import Bot
from app.models.schemas import ApiResponse, RecommendedQuestionDto

router = APIRouter(prefix="/api/v1/bots", tags=["recommend"])


@router.get("/{bot_id}/recommend", response_model=ApiResponse)
async def get_recommended_questions(
    bot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """봇에 등록된 추천 질문 목록 반환"""
    result = await db.execute(
        select(Bot)
        .options(selectinload(Bot.recommended_questions))
        .where(Bot.id == bot_id)
    )
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    return ApiResponse(
        success=True,
        data=[RecommendedQuestionDto(question=q.question).model_dump() for q in bot.recommended_questions],
    )
