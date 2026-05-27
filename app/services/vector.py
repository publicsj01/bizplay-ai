# pgvector 임베딩/검색 서비스 — LangChain PGVector 래퍼
# Spring AI: PGVectorStore + EmbeddingModel 대응
# 벡터 테이블: vector_store (LangChain 기본 테이블명 그대로 사용)

from functools import lru_cache
from typing import Any

from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector as PGVectorStore
from langchain_core.documents import Document as LCDocument

from app.core.config import settings
from app.services.llm import get_embedding_model


# ── PGVector 인스턴스 (싱글턴) ────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_vector_store() -> PGVectorStore:
    """
    LangChain PGVector 인스턴스 반환.
    Spring AI: PGVectorStore(index=HNSW, distance=COSINE, dimensions=1024) 대응
    connection: asyncpg → psycopg3(동기) URL로 변환 (LangChain PGVector는 동기 드라이버 사용)
    """
    sync_url = settings.database_url.replace("+asyncpg", "")
    return PGVector(
        connection=sync_url,
        embeddings=get_embedding_model(),
        collection_name="vector_store",
        use_jsonb=True,
    )


# ── 문서 임베딩 및 저장 ───────────────────────────────────────────────────────

async def embed_and_store(
    chunks: list[str],
    metadata_list: list[dict[str, Any]],
) -> None:
    """
    텍스트 청크를 임베딩하여 PGVector에 저장한다.
    Spring AI: VectorStore.add(documents) 대응
    각 청크 메타데이터에 bot_id, doc_id 필드 필수 (검색 필터에 사용)
    """
    docs = [
        LCDocument(page_content=chunk, metadata=meta)
        for chunk, meta in zip(chunks, metadata_list)
    ]
    store = get_vector_store()
    # LangChain PGVector.add_documents는 동기 — run_in_executor로 래핑
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, store.add_documents, docs)


# ── 벡터 검색 ─────────────────────────────────────────────────────────────────

async def similarity_search(
    query: str,
    bot_id: str,
    top_k: int,
) -> list[LCDocument]:
    """
    bot_id 필터 + 코사인 유사도 검색.
    Spring AI: vectorStore.similaritySearch(SearchRequest.builder()
        .query(query).topK(k).filterExpression("bot_id == 'uuid'").build()) 대응
    """
    store = get_vector_store()
    import asyncio
    loop = asyncio.get_event_loop()

    # LangChain PGVector filter: metadata 필드 기준
    results = await loop.run_in_executor(
        None,
        lambda: store.similarity_search_with_score(
            query,
            k=top_k,
            filter={"bot_id": bot_id},
        ),
    )
    # (Document, score) 튜플 리스트 → Document 리스트 (score를 metadata에 주입)
    docs = []
    for doc, score in results:
        doc.metadata["score"] = float(score)
        docs.append(doc)
    return docs


# ── 문서 삭제 ─────────────────────────────────────────────────────────────────

async def delete_by_doc_id(doc_id: str) -> None:
    """
    특정 doc_id의 모든 벡터 청크를 삭제한다.
    Spring AI: vectorStore.delete(filterExpression("doc_id == 'uuid'")) 대응
    """
    store = get_vector_store()
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: store.delete(filter={"doc_id": doc_id}),
    )
