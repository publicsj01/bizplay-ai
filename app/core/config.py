# 환경변수 설정 — pydantic-settings 기반, .env 파일에서 로드
# Spring AI: application.yml + @ConfigurationProperties → pydantic BaseSettings

from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LlmModelConfig(BaseSettings):
    name: str = "default"
    label: str = "Default LLM"
    base_url: str = "http://localhost:8000/v1"
    api_key: str = "local"
    model: str = "LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct-AWQ"
    temperature: float = 0.0
    max_tokens: int = 2048


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Provider 선택: ollama | openai | anthropic | gemini
    # .env 수정만으로 전환 가능 (Spring AI: app.llm 프로퍼티 대응)
    llm_provider: Literal["ollama", "openai", "anthropic", "gemini"] = "ollama"
    llm_model: str = "llama3.2"

    # Ollama (로컬)
    ollama_base_url: str = "http://localhost:11434"

    # OpenAI 호환 vLLM 서버 (Spring AI: app.llm.models[].base-url)
    vllm_base_url: str = "http://localhost:8000/v1"
    vllm_api_key: str = "local"

    # Anthropic
    anthropic_api_key: str = ""

    # Google Gemini
    gemini_api_key: str = ""

    # Embedding 서버 (Spring AI: app.embed)
    embed_base_url: str = "http://localhost:8001"
    embed_api_key: str = "local"
    embed_model: str = "bge-m3"
    embed_dimensions: int = 1024

    # Reranker (Spring AI: app.reranker)
    reranker_enabled: bool = False
    reranker_base_url: str = ""
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_candidates: int = 20

    # RAG 파라미터 (Spring AI: app.rag)
    rag_chunk_size: int = 1024
    rag_chunk_overlap: int = 200
    rag_top_k: int = 5
    rag_history_turns: int = 5

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/bizplay_chatbot"

    # 파일 업로드 경로 (Spring AI: uploads/ 디렉토리)
    upload_dir: str = "uploads"

    # UI 인증 (Spring AI: app.ui.username/password)
    ui_username: str = "admin"
    ui_password: str = "admin"

    # 기본 법인 코드 (Spring AI: app.tenant.default-corp-no)
    default_corp_no: str = "DEFAULT"


settings = Settings()
