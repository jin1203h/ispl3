-- 대화 이력 관리를 위한 테이블 추가
-- PostgreSQL 17.6

-- chat_sessions (대화 세션)
CREATE TABLE IF NOT EXISTS chat_sessions (
    id SERIAL PRIMARY KEY,
    thread_id VARCHAR(100) UNIQUE NOT NULL, -- LangGraph thread_id
    user_id INTEGER, -- 향후 사용자 인증 추가 시 사용
    title VARCHAR(200), -- 대화 제목 (첫 질문 또는 사용자 지정)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_thread_id ON chat_sessions(thread_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at DESC);

-- chat_messages (대화 메시지)
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    message_metadata JSONB, -- search_results, processing_result, task_results 등
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);




