# 쿼리 의도 분류 + 검색어 재작성 서비스
# Spring AI: QueryReformulationService.java 1:1 대응
# RETRIEVE(문서+히스토리) / HISTORY_ONLY(번역·요약 등 순수 변환) 분기

import re
from enum import Enum

from langchain_core.messages import HumanMessage, SystemMessage

from app.services.llm import get_chat_model


class QueryIntent(str, Enum):
    RETRIEVE = "RETRIEVE"
    HISTORY_ONLY = "HISTORY_ONLY"


# ── Tier 1: 정규식 패턴 (Spring AI: QueryReformulationService 정규식 목록 대응) ─

_PURE_TRANSFORM_PATTERNS = [
    # 번역 (영→한, 한→영, 기타)
    r"(?i)translate\s+(that|it|this)\s+to\s+\w+",
    r"(?i)(영어|한국어|일어|중국어|프랑스어|스페인어)로\s*(번역|바꿔|변환)",
    r"(?i)in\s+(english|korean|japanese|chinese|french|spanish)\s*(please)?$",
    # 요약
    r"(?i)(요약|summarize|summarise|줄여|간단히|짧게|brief)",
    # 단순화
    r"(?i)(더\s*쉽게|쉬운\s*말로|simple|simplify|easier)",
    # 재출력
    r"(?i)(다시\s*말해|repeat\s*that|say\s*that\s*again|다시\s*알려)",
    # 형식 변환
    r"(?i)(bullet|글머리|표로|테이블로|목록으로|list\s*format)",
]

_COMPILED_PATTERNS = [re.compile(p) for p in _PURE_TRANSFORM_PATTERNS]

# ── Tier 2: 순수 변환 예시 (임베딩 유사도용 — 추후 실제 임베딩 비교로 교체 가능)
# Spring AI: 40+ canonical pure-transform examples

_PURE_TRANSFORM_EXAMPLES = [
    "translate that to english",
    "영어로 번역해줘",
    "그걸 영어로 바꿔줘",
    "한국어로 번역해줘",
    "요약해줘",
    "더 짧게 요약해줘",
    "간단히 설명해줘",
    "더 쉽게 설명해줘",
    "쉬운 말로 바꿔줘",
    "방금 한 말 다시 반복해줘",
    "그거 다시 말해줘",
    "bullet point로 정리해줘",
    "표로 만들어줘",
    "summarize what you said",
    "make it shorter",
    "can you simplify that",
    "say that in english please",
    "translate to korean",
    "reformat as a list",
]


def classify_intent(query: str) -> QueryIntent:
    """
    쿼리가 순수 변환(번역·요약·재출력)인지 판단한다.
    Tier 1 정규식 → Tier 2 키워드 포함 체크 순서로 처리.
    Spring AI: QueryReformulationService.classify() 대응
    """
    q_lower = query.lower().strip()

    # Tier 1: 정규식
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(q_lower):
            return QueryIntent.HISTORY_ONLY

    # Tier 2: 예시와 단순 부분 문자열 비교 (임베딩 없는 폴백)
    # Spring AI에서는 임베딩 코사인 유사도 >= 0.85 임계값 사용
    for example in _PURE_TRANSFORM_EXAMPLES:
        if example in q_lower or q_lower in example:
            return QueryIntent.HISTORY_ONLY

    return QueryIntent.RETRIEVE


def is_referential_followup(query: str) -> bool:
    """
    지시 대명사/지시어 기반 후속 질문 감지.
    Spring AI: ChatService.isReferentialFollowup() 대응
    예: "그거 설명해줘", "8번 항목 자세히", "앞서 말한 것"
    """
    patterns = [
        r"(?i)\b(that|it|this|those|these|the above|앞서|그|이|저|위의|방금|아까)\b",
        r"(?i)(point|항목|번호|번)\s*\d+",
        r"(?i)\d+(번|번째|항|조)",
        r"(?i)(explain|describe|elaborate|자세히|더\s*알려|설명해)",
    ]
    q = query.lower()
    for p in patterns:
        if re.search(p, q):
            return True
    return False


async def reformulate_for_search(
    query: str,
    history: list[dict],
) -> str:
    """
    지시어 포함 후속 질문을 독립적인 검색어로 재작성한다.
    Spring AI: QueryReformulationService.reformulate(query, history) LLM 호출 대응
    실패 시 마지막 user 메시지를 prepend하는 폴백 적용.
    """
    if not history:
        return query

    # 히스토리를 텍스트로 직렬화 (최근 4턴만)
    recent = history[-8:]  # 4 turn = user+assistant * 4
    history_text = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'][:400]}"
        for m in recent
    )

    system = SystemMessage(content=(
        "You are a search query rewriter. "
        "Rewrite the follow-up question as a self-contained search query using the conversation history. "
        "Output ONLY the rewritten query, no explanation.\n"
        "Important: 'point N' or '8번 항목' refers to items in the ASSISTANT's last answer, not document articles.\n\n"
        "Examples:\n"
        "History: Assistant: The three main risks are: 1. Market risk 2. Credit risk 3. Operational risk\n"
        "Follow-up: explain point 2\n"
        "Rewritten: Explain credit risk in detail\n\n"
        "History: 어시스턴트: 주요 기능은 1.로그인 2.대시보드 3.보고서 입니다\n"
        "Follow-up: 2번 기능 자세히 설명해줘\n"
        "Rewritten: 대시보드 기능 상세 설명"
    ))
    human = HumanMessage(content=(
        f"Conversation history:\n{history_text}\n\n"
        f"Follow-up question: {query}\n\n"
        "Rewritten standalone search query:"
    ))

    try:
        llm = get_chat_model()
        response = await llm.ainvoke([system, human])
        rewritten = response.content.strip()
        if rewritten:
            return rewritten
    except Exception:
        pass

    # 폴백: 마지막 user 메시지 + 현재 query prepend
    # Spring AI: ChatService.java fallback prepend 로직 대응
    last_user = next(
        (m["content"][:200] for m in reversed(history) if m["role"] == "user"),
        "",
    )
    return f"{last_user} {query}" if last_user else query
