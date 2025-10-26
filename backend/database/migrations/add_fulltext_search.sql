-- ================================================
-- Migration: Full-Text Search 지원 추가
-- 목적: document_chunks 테이블에 tsvector 컬럼 및 GIN 인덱스 추가
-- 날짜: 2025-10-16
-- 참고: content_tsv는 애플리케이션 레벨에서 관리 (트리거 미사용)
-- ================================================

-- 1. tsvector 컬럼 추가
-- content 컬럼의 Full-Text Search를 위한 tsvector 타입 컬럼
ALTER TABLE document_chunks 
ADD COLUMN IF NOT EXISTS content_tsv tsvector;

-- 2. GIN 인덱스 생성
-- CONCURRENTLY 옵션: 인덱스 생성 중 테이블 락 최소화
-- GIN (Generalized Inverted Index): Full-Text Search에 최적화된 인덱스
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chunks_content_tsv 
ON document_chunks USING GIN(content_tsv);

-- 3. 마이그레이션 완료 확인
DO $$
DECLARE
    column_exists BOOLEAN;
    index_exists BOOLEAN;
BEGIN
    -- 컬럼 존재 확인
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'document_chunks' 
        AND column_name = 'content_tsv'
    ) INTO column_exists;
    
    -- 인덱스 존재 확인
    SELECT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'document_chunks' 
        AND indexname = 'idx_chunks_content_tsv'
    ) INTO index_exists;
    
    -- 결과 출력
    RAISE NOTICE '✅ Full-Text Search 마이그레이션 완료';
    RAISE NOTICE '   - content_tsv 컬럼 추가: %', CASE WHEN column_exists THEN '완료' ELSE '실패' END;
    RAISE NOTICE '   - GIN 인덱스 생성: %', CASE WHEN index_exists THEN '완료' ELSE '실패' END;
    RAISE NOTICE '   - content_tsv는 애플리케이션에서 관리됩니다';
    
    -- 검증 실패 시 경고
    IF NOT column_exists OR NOT index_exists THEN
        RAISE WARNING '⚠️ 일부 마이그레이션 단계가 실패했습니다. 로그를 확인하세요.';
    END IF;
END $$;

