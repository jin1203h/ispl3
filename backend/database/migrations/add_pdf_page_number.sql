-- Migration: Add pdf_page_number column
-- Date: 2025-10-21
-- Description: PDF 내부 인쇄 페이지 번호 컬럼 추가

-- 1. 컬럼 추가
ALTER TABLE document_chunks 
ADD COLUMN IF NOT EXISTS pdf_page_number INTEGER;

-- 2. 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_chunks_pdf_page ON document_chunks(pdf_page_number);

-- 3. 주석 추가
COMMENT ON COLUMN document_chunks.page_number IS '물리적 순서 (1, 2, 3...)';
COMMENT ON COLUMN document_chunks.pdf_page_number IS 'PDF 내부 인쇄 페이지 번호';

-- 4. 기존 데이터 마이그레이션 (선택사항)
-- 기존 page_number를 pdf_page_number로 복사
-- UPDATE document_chunks SET pdf_page_number = page_number WHERE pdf_page_number IS NULL;

