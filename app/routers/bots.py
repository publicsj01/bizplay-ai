# 봇 관리 라우터 — Spring AI BotController.java 1:1 대응
# CRUD + enable/disable + statistics + sessions

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.models.entities import (
    Bot,
    BotRecommendedQuestion,
    ChatMessage,
    ChatSession,
    Document,
)
from app.models.schemas import (
    ApiResponse,
    BotCreateRequest,
    BotResponse,
    BotStatisticsResponse,
    BotUpdateRequest,
    DailyStatisticsItem,
    KeywordItem,
    RecommendedQuestionDto,
)

router = APIRouter(prefix="/api/v1/bots", tags=["bots"])


def _to_response(bot: Bot) -> BotResponse:
    return BotResponse(
        id=bot.id,
        corp_no=bot.corp_no,
        name=bot.name,
        description=bot.description,
        contact_email=bot.contact_email,
        contact_phone=bot.contact_phone,
        system_prompt=bot.system_prompt,
        source_expose=bot.source_expose,
        llm_model=bot.llm_model,
        llm_temperature=bot.llm_temperature,
        max_answer_length=bot.max_answer_length,
        history_turns=bot.history_turns,
        top_k=bot.top_k,
        disabled=bot.disabled,
        telegram_configured=bool(bot.telegram_bot_token),
        telegram_bot_username=bot.telegram_bot_username,
        telegram_configured_at=bot.telegram_configured_at,
        kakao_configured=bool(bot.kakao_webhook_secret),
        kakao_bot_name=bot.kakao_bot_name,
        kakao_configured_at=bot.kakao_configured_at,
        recommended_questions=[
            RecommendedQuestionDto(question=q.question) for q in (bot.recommended_questions or [])
        ],
        created_at=bot.created_at,
        updated_at=bot.updated_at,
    )


@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_bot(
    req: BotCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """Spring AI: BotController.create() 대응. 새 봇은 disabled=True로 생성됨"""
    bot = Bot(
        corp_no=req.corp_no or settings.default_corp_no,
        name=req.name,
        description=req.description,
        contact_email=str(req.contact_email) if req.contact_email else None,
        contact_phone=req.contact_phone,
        system_prompt=req.system_prompt,
        source_expose=req.source_expose,
        llm_model=req.llm_model,
        llm_temperature=req.llm_temperature,
        max_answer_length=req.max_answer_length,
        history_turns=req.history_turns,
        top_k=req.top_k,
        disabled=True,  # Spring AI: 신규 봇은 비활성 상태로 생성
    )
    db.add(bot)
    await db.flush()

    for q in req.recommended_questions:
        db.add(BotRecommendedQuestion(bot_id=bot.id, question=q.question))

    await db.flush()
    await db.refresh(bot, ["recommended_questions"])
    return ApiResponse(success=True, data=_to_response(bot).model_dump())


@router.get("", response_model=ApiResponse)
async def list_bots(db: AsyncSession = Depends(get_db)) -> ApiResponse:
    result = await db.execute(
        select(Bot)
        .options(selectinload(Bot.recommended_questions))
        .order_by(Bot.created_at.desc())
    )
    bots = result.scalars().all()
    return ApiResponse(success=True, data=[_to_response(b).model_dump() for b in bots])


@router.get("/{bot_id}", response_model=ApiResponse)
async def get_bot(bot_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ApiResponse:
    result = await db.execute(
        select(Bot)
        .options(selectinload(Bot.recommended_questions))
        .where(Bot.id == bot_id)
    )
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return ApiResponse(success=True, data=_to_response(bot).model_dump())


@router.put("/{bot_id}", response_model=ApiResponse)
async def update_bot(
    bot_id: uuid.UUID,
    req: BotUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """Spring AI: BotController.update() — PATCH 시맨틱"""
    result = await db.execute(
        select(Bot)
        .options(selectinload(Bot.recommended_questions))
        .where(Bot.id == bot_id)
    )
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    for field, value in req.model_dump(exclude_unset=True, exclude={"recommended_questions"}).items():
        if value is not None:
            setattr(bot, field, value)

    if req.recommended_questions is not None:
        for q in list(bot.recommended_questions):
            await db.delete(q)
        await db.flush()
        for q in req.recommended_questions:
            db.add(BotRecommendedQuestion(bot_id=bot.id, question=q.question))

    await db.flush()
    await db.refresh(bot, ["recommended_questions"])
    return ApiResponse(success=True, data=_to_response(bot).model_dump())


@router.patch("/{bot_id}/enable", response_model=ApiResponse)
async def enable_bot(bot_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ApiResponse:
    bot = await db.get(Bot, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    bot.disabled = False
    return ApiResponse(success=True, message="Bot enabled")


@router.patch("/{bot_id}/disable", response_model=ApiResponse)
async def disable_bot(bot_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ApiResponse:
    bot = await db.get(Bot, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    bot.disabled = True
    return ApiResponse(success=True, message="Bot disabled")


@router.delete("/{bot_id}", response_model=ApiResponse)
async def delete_bot(bot_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ApiResponse:
    """Spring AI: cascade 삭제 (documents, sessions, vector chunks)"""
    bot = await db.get(Bot, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    # 벡터 청크 삭제 (bot_id 기준)
    from app.services.vector import get_vector_store
    import asyncio
    store = get_vector_store()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: store.delete(filter={"bot_id": str(bot_id)}))

    await db.delete(bot)
    return ApiResponse(success=True, message="Bot deleted")


@router.get("/{bot_id}/statistics", response_model=ApiResponse)
async def get_statistics(bot_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ApiResponse:
    """Spring AI: BotController.getStatistics() 대응"""
    doc_count = await db.scalar(select(func.count()).where(Document.bot_id == bot_id))
    session_count = await db.scalar(select(func.count()).where(ChatSession.bot_id == bot_id))
    msg_count = await db.scalar(
        select(func.count())
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .where(ChatSession.bot_id == bot_id)
    )
    input_tokens = await db.scalar(
        select(func.coalesce(func.sum(ChatMessage.input_tokens), 0))
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .where(ChatSession.bot_id == bot_id)
    )
    output_tokens = await db.scalar(
        select(func.coalesce(func.sum(ChatMessage.output_tokens), 0))
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .where(ChatSession.bot_id == bot_id)
    )

    return ApiResponse(
        success=True,
        data=BotStatisticsResponse(
            bot_id=bot_id,
            document_count=doc_count or 0,
            session_count=session_count or 0,
            message_count=msg_count or 0,
            total_input_tokens=input_tokens or 0,
            total_output_tokens=output_tokens or 0,
        ).model_dump(),
    )


@router.get("/{bot_id}/statistics/daily", response_model=ApiResponse)
async def get_daily_statistics(
    bot_id: uuid.UUID,
    window_days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    since = datetime.utcnow() - timedelta(days=window_days)
    result = await db.execute(
        select(
            func.date(ChatSession.created_at).label("date"),
            func.count(ChatSession.id).label("session_count"),
        )
        .where(ChatSession.bot_id == bot_id, ChatSession.created_at >= since)
        .group_by(func.date(ChatSession.created_at))
        .order_by(func.date(ChatSession.created_at))
    )
    rows = result.all()
    return ApiResponse(
        success=True,
        data=[DailyStatisticsItem(date=str(r.date), session_count=r.session_count, message_count=0).model_dump() for r in rows],
    )


@router.get("/{bot_id}/sessions", response_model=ApiResponse)
async def get_sessions(bot_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ApiResponse:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.bot_id == bot_id)
        .order_by(ChatSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return ApiResponse(
        success=True,
        data=[
            {"id": str(s.id), "channel": s.channel, "created_at": s.created_at.isoformat()}
            for s in sessions
        ],
    )
