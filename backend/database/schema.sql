-- ISPL 데이터베이스 스키마
-- PostgreSQL 17.6 + pgvector extension

-- pgvector extension 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- users (사용자 정보)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE,
    email VARCHAR(100) UNIQUE,
    full_name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user', -- 'admin', 'user', 'agent'
    insurance_preferences JSONB, -- 관심 보험 유형 등
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- documents (문서 메타데이터)
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    document_type VARCHAR(50) NOT NULL, -- 'policy', 'clause', 'faq', 'guideline'
    insurance_type VARCHAR(50), -- 'life', 'auto', 'health', 'property'
    company_name VARCHAR(100),
    version VARCHAR(20),
    effective_date DATE,
    expiry_date DATE,
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'inactive', 'archived'
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_timestamp TIMESTAMP,
    total_pages INTEGER,
    processing_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    created_by INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_insurance_type ON documents(insurance_type);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_effective_date ON documents(effective_date);

-- document_chunks (벡터화된 청크)
CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_type VARCHAR(20) NOT NULL, -- 'text', 'table', 'image'
    page_number INTEGER, -- Vision의 물리적 순서 (1, 2, 3...)
    pdf_page_number INTEGER, -- PDF 내부 인쇄 페이지 번호
    section_title VARCHAR(200),
    clause_number VARCHAR(50),
    content TEXT NOT NULL,
    content_hash VARCHAR(64), -- SHA-256 해시로 중복 방지
    token_count INTEGER,
    metadata JSONB, -- 구조적 정보 저장
    embedding VECTOR(1536), -- OpenAI text-embedding-3-large
    confidence_score FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_chunk_per_doc UNIQUE(document_id, chunk_index)
);

-- 벡터 검색을 위한 HNSW 인덱스
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON document_chunks 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 32, ef_construction = 200);

-- 일반 인덱스
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_type ON document_chunks(chunk_type);
CREATE INDEX IF NOT EXISTS idx_chunks_page ON document_chunks(page_number);
CREATE INDEX IF NOT EXISTS idx_chunks_pdf_page ON document_chunks(pdf_page_number);
CREATE INDEX IF NOT EXISTS idx_chunks_clause ON document_chunks(clause_number);
CREATE INDEX IF NOT EXISTS idx_chunks_hash ON document_chunks(content_hash);

-- processing_logs (처리 로그)
CREATE TABLE IF NOT EXISTS processing_logs (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    processing_stage VARCHAR(50), -- 'extraction', 'chunking', 'embedding', 'indexing'
    status VARCHAR(20), -- 'started', 'completed', 'failed'
    message TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_processing_logs_document_id ON processing_logs(document_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_stage ON processing_logs(processing_stage);

-- search_logs (검색 로그)
CREATE TABLE IF NOT EXISTS search_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    query TEXT NOT NULL,
    query_intent VARCHAR(50), -- 의도 분류 결과
    search_type VARCHAR(20), -- 'vector', 'keyword', 'hybrid'
    results_count INTEGER,
    top_similarity_score FLOAT,
    selected_document_ids INTEGER[], -- 사용자가 클릭한 문서
    response_time_ms INTEGER,
    user_feedback VARCHAR(20), -- 'positive', 'negative', null
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_search_logs_user_id ON search_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_search_logs_created_at ON search_logs(created_at);

