# LLM Provider 추상화 — .env의 LLM_PROVIDER 값으로 분기
# Spring AI: SpringAiConfig.java chatClientRegistry 대응
# Ollama(로컬) / Anthropic / OpenAI 전환 시 .env만 수정하면 됨

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from app.core.config import settings


# ── Chat 모델 팩토리 ──────────────────────────────────────────────────────────

def get_chat_model(
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    model_override: str | None = None,
) -> BaseChatModel:
    """
    LLM_PROVIDER 환경변수에 따라 Chat 모델을 반환한다.
    per-bot temperature/max_tokens는 Bot 설정에서 오버라이드된다.
    Spring AI: ChatClientRegistry.get(bot.getLlmModel()) 대응
    """
    temp = temperature if temperature is not None else settings.llm_temperature if hasattr(settings, "llm_temperature") else 0.0
    tokens = max_tokens if max_tokens is not None else 2048
    model_name = model_override or settings.llm_model

    if settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=model_name,
            temperature=temp,
            num_predict=tokens,
        )

    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            api_key=settings.anthropic_api_key,
            model=model_name,
            temperature=temp,
            max_tokens=tokens,
        )

    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            base_url=settings.vllm_base_url,
            api_key=settings.vllm_api_key,
            model=model_name,
            temperature=temp,
            max_tokens=tokens,
        )

    raise ValueError(f"지원하지 않는 LLM_PROVIDER: {settings.llm_provider}")


# ── Embedding 모델 팩토리 ─────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_embedding_model() -> Embeddings:
    """
    임베딩 모델을 반환한다. 항상 동일한 인스턴스를 재사용한다.
    Spring AI: EmbeddingModel (OpenAI 호환 embedding 서버) 대응
    Ollama 사용 시에도 별도 embedding 서버(bge-m3)를 가리킨다.
    """
    if settings.llm_provider == "ollama":
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(
            base_url=settings.embed_base_url,
            model=settings.embed_model,
        )

    if settings.llm_provider == "anthropic":
        # Anthropic은 자체 임베딩 API 없음 — OpenAI 호환 서버로 fallback
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            base_url=settings.embed_base_url,
            api_key=settings.embed_api_key,
            model=settings.embed_model,
        )

    if settings.llm_provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            base_url=settings.embed_base_url,
            api_key=settings.embed_api_key,
            model=settings.embed_model,
        )

    raise ValueError(f"지원하지 않는 LLM_PROVIDER: {settings.llm_provider}")


# ── LLM 모델 목록 (Spring AI: GET /api/v1/rag/chat/models) ───────────────────

def list_available_models() -> list[dict]:
    """등록된 모델 목록 반환. Spring AI: chatClientRegistry.keySet() 대응"""
    return [
        {
            "name": settings.llm_model,
            "label": f"{settings.llm_provider.capitalize()} / {settings.llm_model}",
            "model": settings.llm_model,
        }
    ]
