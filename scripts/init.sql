-- pgvector 확장 활성화 (Spring AI: initialize-schema 대응)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- bots
CREATE TABLE IF NOT EXISTS bots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    corp_no VARCHAR(50) NOT NULL DEFAULT 'DEFAULT',
    name VARCHAR(255) NOT NULL,
    description TEXT,
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    system_prompt TEXT,
    source_expose BOOLEAN NOT NULL DEFAULT TRUE,
    llm_model VARCHAR(255) NOT NULL,
    llm_temperature NUMERIC(3,2) NOT NULL DEFAULT 0.0,
    max_answer_length INTEGER NOT NULL DEFAULT 2048,
    history_turns INTEGER NOT NULL DEFAULT 5,
    top_k INTEGER NOT NULL DEFAULT 5,
    disabled BOOLEAN NOT NULL DEFAULT TRUE,
    telegram_bot_token VARCHAR(255),
    telegram_bot_username VARCHAR(255),
    telegram_last_offset BIGINT,
    telegram_configured_at TIMESTAMPTZ,
    kakao_webhook_secret VARCHAR(255),
    kakao_bot_name VARCHAR(255),
    kakao_configured_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    content_type VARCHAR(100),
    embedding_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- chat_sessions
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    channel VARCHAR(20) NOT NULL DEFAULT 'web',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- chat_messages
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    lang VARCHAR(10),
    input_tokens INTEGER,
    output_tokens INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- bot_recommended_questions
CREATE TABLE IF NOT EXISTS bot_recommended_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    question TEXT NOT NULL
);

-- LangChain PGVector 테이블 (langchain_pg_collection + langchain_pg_embedding)
-- LangChain이 자동 생성하므로 CREATE IF NOT EXISTS만 명시
CREATE TABLE IF NOT EXISTS langchain_pg_collection (
    uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR NOT NULL UNIQUE,
    cmetadata JSONB
);

CREATE TABLE IF NOT EXISTS langchain_pg_embedding (
    id VARCHAR PRIMARY KEY,
    collection_id UUID REFERENCES langchain_pg_collection(uuid) ON DELETE CASCADE,
    embedding vector(768),
    document TEXT,
    cmetadata JSONB,
    custom_id VARCHAR
);

CREATE INDEX IF NOT EXISTS idx_langchain_pg_embedding_collection
    ON langchain_pg_embedding(collection_id);

-- Spring AI pgvector HNSW 인덱스와 동일한 성능 목표
CREATE INDEX IF NOT EXISTS idx_langchain_pg_embedding_vector
    ON langchain_pg_embedding USING hnsw (embedding vector_cosine_ops);
