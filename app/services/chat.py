# RAG 채팅 파이프라인 — Spring AI ChatService.java 1:1 대응
# 흐름: 봇 검증 → 의도 분류 → 검색어 재작성 → 벡터 검색 → (리랭크) → LLM 생성 → 메시지 저장

import uuid
from typing import Any

from fastapi import HTTPException, status
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.entities import Bot, ChatMessage, ChatSession
from app.models.schemas import ChatRequest, ChatResponse, ChatSource
from app.services.llm import get_chat_model
from app.services.query_reformulation import (
    QueryIntent,
    classify_intent,
    is_referential_followup,
    reformulate_for_search,
)
from app.services.vector import similarity_search

# LLM이 답변 불가 시 출력하는 구문 패턴 (Spring AI: ChatService._REFUSAL_PHRASES)
_REFUSAL_PHRASES = [
    "i don't have enough information",
    "i cannot find",
    "no relevant information",
    "관련 정보를 찾을 수 없",
    "충분한 정보가 없",
    "해당 내용을 찾을 수 없",
    "문서에서 찾을 수 없",
]

_DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant. "
    "Answer the user's question based on the provided context. "
    "If you cannot find relevant information in the context, "
    "say so clearly rather than making up an answer."
)

# 히스토리 메시지당 최대 문자 수 (Spring AI: 4000자 제한)
_MAX_HISTORY_CHARS = 4000


async def handle_chat(db: AsyncSession, req: ChatRequest) -> ChatResponse:
    """
    RAG 채팅 메인 파이프라인.
    Spring AI: ChatService.chat(ChatRequest) 대응
    """
    # 1. 봇 로드 및 검증
    bot = await db.get(Bot, req.bot_id)
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
    if bot.disabled:
        # Spring AI: 비활성 봇 → 409 CONFLICT
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bot is disabled")

    # 2. 세션 조회 또는 생성
    session = await _get_or_create_session(db, bot, req)

    # 3. 히스토리 로드 (historyTurns 제한)
    history = await _load_history(db, session.id, bot.history_turns)

    # 4. 의도 분류 (Spring AI: QueryReformulationService.classify())
    intent = classify_intent(req.query)

    # 5. 검색 & 생성 분기
    context_docs: list[Any] = []
    search_query = req.query

    if intent == QueryIntent.RETRIEVE:
        # 지시어 포함 후속 질문이면 검색어 재작성
        if history and is_referential_followup(req.query):
            search_query = await reformulate_for_search(req.query, history)

        # 벡터 검색 (bot_id 필터)
        top_k = bot.top_k or settings.rag_top_k
        fetch_k = max(top_k, settings.reranker_candidates) if settings.reranker_enabled else top_k
        context_docs = await similarity_search(search_query, str(bot.bot_id if hasattr(bot, "bot_id") else bot.id), fetch_k)

        # 리랭킹 (활성화된 경우)
        if settings.reranker_enabled and len(context_docs) > top_k:
            context_docs = await _rerank(req.query, context_docs, top_k)
        else:
            context_docs = context_docs[:top_k]

    # 6. LLM 프롬프트 조합 및 생성
    answer, input_tokens, output_tokens = await _generate(
        bot=bot,
        query=req.query,
        history=history,
        context_docs=context_docs,
        intent=intent,
    )

    # 7. 메시지 영속화 (Spring AI: ChatService.persistMessages())
    await _save_messages(
        db=db,
        session_id=session.id,
        query=req.query,
        answer=answer,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    # 8. 소스 Attribution 조합
    sources = _build_sources(context_docs, answer, bot.source_expose)

    return ChatResponse(
        answer=answer,
        session_id=session.id,
        sources=sources,
    )


async def _get_or_create_session(
    db: AsyncSession, bot: Bot, req: ChatRequest
) -> ChatSession:
    if req.session_id:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == req.session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        # Spring AI: 다른 봇 세션 재사용 시 400
        if session.bot_id != bot.id:
            raise HTTPException(status_code=400, detail="Session belongs to a different bot")
        return session

    session = ChatSession(
        bot_id=bot.id,
        channel=req.channel or "web",
    )
    db.add(session)
    await db.flush()
    return session


async def _load_history(
    db: AsyncSession,
    session_id: uuid.UUID,
    history_turns: int,
) -> list[dict]:
    """최근 N턴의 메시지를 role/content dict 리스트로 반환"""
    if history_turns == 0:
        return []

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(history_turns * 2)  # 1턴 = user + assistant
    )
    messages = result.scalars().all()
    messages = list(reversed(messages))

    return [
        {
            "role": m.role,
            # Spring AI: 히스토리 메시지 4000자 truncation
            "content": m.content[:_MAX_HISTORY_CHARS],
        }
        for m in messages
    ]


async def _generate(
    bot: Bot,
    query: str,
    history: list[dict],
    context_docs: list[Any],
    intent: QueryIntent,
) -> tuple[str, int, int]:
    """LLM 호출 및 토큰 수 반환"""
    system_prompt = bot.system_prompt or _DEFAULT_SYSTEM_PROMPT
    temp = float(bot.llm_temperature)
    max_tokens = bot.max_answer_length

    llm = get_chat_model(temperature=temp, max_tokens=max_tokens)

    messages = [SystemMessage(content=system_prompt)]

    # 히스토리 메시지 추가 (HISTORY_ONLY는 히스토리만, RETRIEVE는 히스토리+컨텍스트)
    for h in history:
        if h["role"] == "user":
            messages.append(HumanMessage(content=h["content"]))
        else:
            from langchain_core.messages import AIMessage
            messages.append(AIMessage(content=h["content"]))

    # 컨텍스트 조합 (RETRIEVE 전용)
    user_content = query
    if intent == QueryIntent.RETRIEVE and context_docs:
        context_text = "\n\n---\n\n".join(doc.page_content for doc in context_docs)
        user_content = (
            f"Context:\n{context_text}\n\n"
            f"Question: {query}"
        )
    elif intent == QueryIntent.RETRIEVE and not context_docs:
        # Spring AI: no-documents path — LLM에게 컨텍스트 없음을 알림
        user_content = (
            f"No relevant documents were found.\n\n"
            f"Question: {query}"
        )

    messages.append(HumanMessage(content=user_content))

    response = await llm.ainvoke(messages)
    answer = response.content.strip()

    # 토큰 수 추출 (Spring AI: ChatMessage.inputTokens/outputTokens 대응)
    usage = getattr(response, "usage_metadata", None) or {}
    input_tokens = usage.get("input_tokens", 0) if isinstance(usage, dict) else getattr(usage, "input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0) if isinstance(usage, dict) else getattr(usage, "output_tokens", 0)

    return answer, input_tokens, output_tokens


async def _rerank(
    query: str,
    docs: list[Any],
    top_k: int,
) -> list[Any]:
    """
    Cross-encoder 리랭킹 (BAAI/bge-reranker-v2-m3).
    Spring AI: RerankerService.rerank() 대응
    현재는 score 기준 정렬만 수행 (실제 리랭커 서버 연동은 추후 구현)
    """
    # TODO: settings.reranker_base_url로 vLLM reranker API 호출
    return sorted(docs, key=lambda d: d.metadata.get("score", 0.0), reverse=True)[:top_k]


async def _save_messages(
    db: AsyncSession,
    session_id: uuid.UUID,
    query: str,
    answer: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    user_msg = ChatMessage(session_id=session_id, role="user", content=query)
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=answer,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    db.add(user_msg)
    db.add(assistant_msg)
    await db.flush()


def _build_sources(
    docs: list[Any],
    answer: str,
    source_expose: bool,
) -> list[ChatSource]:
    """
    소스 목록 조합. source_expose=False 또는 LLM 거부 응답이면 빈 리스트 반환.
    Spring AI: ChatService.buildSources() 대응
    """
    if not source_expose:
        return []

    answer_lower = answer.lower()
    if any(phrase in answer_lower for phrase in _REFUSAL_PHRASES):
        return []

    sources = []
    for doc in docs:
        meta = doc.metadata
        snippet = doc.page_content[:300]
        doc_id = meta.get("doc_id", "")
        sources.append(
            ChatSource(
                doc_id=doc_id,
                title=meta.get("title", ""),
                file_name=meta.get("file_name", ""),
                snippet=snippet,
                score=round(meta.get("score", 0.0), 4),
                chunk_index=meta.get("chunk_index", 0),
                document_url=f"/api/v1/rag/documents/{doc_id}/download",
            )
        )

    return sources
