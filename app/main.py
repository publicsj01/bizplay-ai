# FastAPI 애플리케이션 엔트리포인트
# Spring AI: BizPlayChatbotApplication.java 대응

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import bots, chat, corp_groups, corps, documents, recommend


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 업로드 디렉토리 초기화
    from pathlib import Path
    from app.core.config import settings
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="BizPlay AI Chatbot API",
    description="Spring AI RAG Chatbot → FastAPI 마이그레이션",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Spring AI: GlobalExceptionHandler.java 대응"""
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc)},
    )


app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(bots.router)
app.include_router(recommend.router)
app.include_router(corp_groups.router)
app.include_router(corps.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
