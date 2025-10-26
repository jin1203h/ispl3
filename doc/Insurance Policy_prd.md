# 보험약관 기반 Agentic AI PRD (Product Requirements Document)

## 1. 서비스 목적 및 개요
- 생성형 AI를 활용하여 약관을 전처리, 요약, 임베딩 후 벡터DB에 저장
- 사용자의 자연어 질의에 대해 관련 약관을 검색 및 답변 제공
- 파일 업로드 지원
- 약관의 통합 관리 및 활용 편의성 극대화
    - 약관 질의 즉시 응답(예: "골절 시 보장 여부?")
    - 타 보험사 약관 비교, 설계사 교육, 계약 특약 확인 지원


## 2. 주요 기능 요건

### 2.1 약관 업로드
- 지원 파일: PDF
- 파일 업로드 → 전처리 → Markdown 변환 → 요약 → 임베딩 → 벡터DB 저장
- 결과를 업로드 시점에 사용자에게 제공
- 원본/Markdown 파일은 로컬에 저장, Markdown 내용은 벡터DB에 저장
- 파일 저장 구조:
  uploads/
    ├── documents/
    │   ├── {original_filename}_{document_id}.pdf    # 원본 PDF
    │   ├── {original_filename}_{document_id}.md     # 처리된 Markdown
    ├── images/           # 추출된 이미지
    │   ├── {document_id}/
    │   │   ├── page_{n}_img_{m}.png
    └── temp/             # 임시 처리 파일
- 파일 명명 규칙:
  - document_id: DB의 documents.id
  - 타임스탬프 포함: {filename}_{document_id}_{timestamp}

### 2.2 전처리
- 하이브리드 PDF 전처리: 직접 추출 + 멀티모달 AI 병합 방식
  텍스트, 표, 이미지를 포함한 PDF 파일을 두 가지 방식으로 동시 처리한 후 최종 병합하는 하이브리드 접근법

### 2.2.1 초기 분석 및 경로 분기

### 2.2.1.1 PDF 분석
- PDF 파일 열기 및 전체 페이지 수 파악

### 2.2.1.2 병렬 처리 경로 설정
- 직접 추출 경로 항상 활성화  
- 멀티모달 AI 경로 항상 활성화  
- 워커 수(멀티스레드/멀티프로세스) 결정

### 2.2.2 Path 1: PDF에서 직접 텍스트 추출

### 2.2.2.1 PDF 파싱 및 텍스트 추출
- PyMuPDF4LLM 활용하여 PDF를 Markdown으로 변환  
- 페이지별 청킹 옵션 적용, 헤더/번호 기반 의미 단위 분리

### 2.2.2.2 표 및 이미지 객체 추출
- Markdown 내 ‘|’ 구문을 기준으로 표 감지 및 파싱  
- 이미지 링크 또는 ‘![]()’ 구문으로 이미지 감지  
- 표와 이미지를 별도 구조로 저장하여 메타데이터 부여

### 2.2.2.3 구조화
- 텍스트 블록, 표, 이미지별로 세분화하여 리스트 저장  
- 각 청크에 페이지 번호, 섹션 번호, 인덱스, 유형, 해시 등을 메타데이터로 부여

### 2.2.3 Path 2: PDF→이미지 변환 + 멀티모달 AI 활용

### 2.2.3.1 PDF를 고해상도 이미지로 변환
- pdf2image 라이브러리 사용하여 페이지별 PNG 이미지 생성  
- 커스텀 DPI(300 이상), 스레드 수 조절

### 2.2.3.2 이미지 전처리
- 그레이스케일 변환
- 적응적 이진화 (Thresholding)
- 미디언 블러 또는 노이즈 제거
- 기울기 보정 (스키우 명령 등)

### 2.2.3.3 멀티모달 AI 입력 준비
- 이미지와 함께 텍스트(초기 OCR 결과 또는 텍스트 추출 필요시)로 인풋 포장
- 멀티모달 모델(GPT-4 Vision) 지원 포맷으로 이미지와 텍스트 정보 세팅
- 이미지 내 텍스트 영역 검출(ROI+OCR) 후 텍스트 보조

### 2.2.3.4 멀티모달 AI 추론 수행
- 이미지+텍스트를 동시에 모델에 입력  
- 이미지 설명, 표 구조, 텍스트 문맥의 합산된 추상적 텍스트 출력  
- 결과를 텍스트 블록, 표 재구성, 이미지 설명으로 정제

### 2.2.3.5 결과 후처리
- 멀티모달 AI 추론 결과의 텍스트와 표 구조, 이미지 설명 텍스트 정제  
- 신뢰도 점수, 메타데이터 부여

### 2.2.4 결과 통합 및 병합

### 2.2.4.1 페이지별 콘텐츠 정렬  
- Path 1과 Path 2의 결과를 페이지 순서에 맞게 병렬 정렬  
- SequenceMatcher 또는 유사도 기반 매핑 수행

### 2.2.4.2 유사도 기반 중복 감지 및 선택  
- 텍스트 유사도(코사인+시퀀스) 계산  
- 중복 청크는 신뢰도 최고쪽 선택 또는 병합  
- 병합 후 하나의 통합 결과 생성

### 2.2.4.3 최종 병합 및 정리
- 텍스트, 표, 이미지 설명별로 누락 없이 포함  
- 신뢰도와 품질에 따라 최적 구성  

### 2.2.4.4 구조화된 출력 생성
- 텍스트, 표, 이미지 설명을 하나의 문서 흐름으로 조립
- 마크다운 포맷으로 최종 생성

### 2.2.5 최종 통합 및 품질 검증

### 2.2.5.1 전체 품질 점수 계산
- 텍스트·표·이미지 완전성 비율 산출
- 병합 성공률 기반 가중 평균으로 최종 점수 산출

### 2.2.5.2 품질 검증
- 완전성 검사(블록 수 대비 점수)
- 일관성 검사(중복 여부)
- 정확도 추정(신뢰도 평균)
- 검증 결과(status, 이슈) 메타데이터로 포함

### 2.2.6 임베딩
- chunking : Fixed-size Chunking
- chunk size : 1,000 토큰
- overlap : 50–100 토큰
- 표 chunk : 전체 표 단위로 하나의 chunk
- 이미지 chunk : 이미지 설명(ALT 텍스트)과 주변 텍스트를 포함해 200–400 토큰
- 임베딩 모델 : OpenAI text-embedding-3-large
- 차원수 : 1,536

### 2.2.7 벡터DB 저장
- DB : postgreSQL + pgvector
- 인덱싱 : HNSW (Hierarchical Navigable Small World)
- 유사도 측정 방식 : Cosine Similarity
- 차원수 : 1,536

### 2.3 약관 검색
- 사용자 질의 → 쿼리 전처리 → 임베딩 생성 → 벡터 검색 → 컨텍스트 구성 → LLM 응답 생성 → 후처리 → 사용자 UI
- 통합검색 및 개별 약관 지정 검색
- 유사도 순으로 결과 반환
- 검색 결과 기반 답변 생성
- LLM 서비스: OpenAI GPT-4
- 임베딩 모델: text-embedding-3-large

### 2.3.1 질의 전처리 및 분석 단계

### 2.3.1.1 사용자 입력 정규화
- 맞춤법 검사 : py-hanspell - 한글 맞춤법 오류 자동 수정  
- 전문용어 표준화 : 
  - 파일로 관리 : term_dictionary(original, normalized)  
  - 동의어 그룹핑 : "보험금/급여금/지급금" → "보험금"
  - 약어 확장 : "CI" → "중대한질병"
- 불완전 질의 감지: 모호한 질문 식별 및 명확화 요청  

### 2.3.1.2 질의 의도 분류
- 키워드 매칭으로 의도 패턴 분류  
- 보험료, 보장내용, 청구절차, 해지환급, 면책조항 등으로 분류  

### 2.3.1.3 컨텍스트 보강
- 사용자 프로필 반영하여 개인화  
- 동의어 확장으로 검색 범위 확대  

### 2.3.2 벡터 검색 및 컨텍스트 구성

### 2.3.2.1 하이브리드 검색 전략
- 쿼리 임베딩 생성  
- 벡터 유사도 검색과 키워드 검색 병행  
- 결과 융합 및 재순위화  

### 2.3.2.2 검색 결과 필터링
- 문서 타입, 시행 중인 약관만 대상  
- 유사도 임계값(0.7 이상) 적용 : Cosine Similarity 기준

### 2.3.2.3 컨텍스트 최적화
- 최대 토큰 수(8000) 내에서 청크 선택  

### 2.3.3 LLM 프롬프트 엔지니어링 및 응답 생성

### 2.3.3.1 시스템 프롬프트 설계
- 당신은 보험약관 전문 상담사입니다. 다음 규칙을 반드시 준수하세요:
    정확성 보장: 제공된 약관 내용에만 기반하여 답변하세요.
    근거 제시: 모든 답변에 해당 약관 조항을 인용하세요.
    한계 인정: 제공된 자료에 없는 내용은 "해당 정보가 약관에 명시되어 있지 않습니다"라고 답하세요.
    명확한 구조: 답변을 ①직접 답변 ②관련 약관 ③주의사항 순으로 구성하세요.
    금지사항: 추측, 일반 상식, 다른 보험사 정보는 절대 사용하지 마세요.

### 2.3.3.2 할루시네이션 방지 기법
- 응답에 반드시 약관 조항번호 인용  
- 생성 답변을 원본 컨텍스트와 재대조  
- 모호 시 “명확하지 않습니다” 명시  

### 2.3.3.3 응답 생성 파이프라인
- 컨텍스트 구성
- 프롬프트 조립 : 시스템 프롬프트 + 컨텍스트 + 사용자 질의
- LLM 호출 : GPT-4 API 호출 (temperature: 0.1)
- 응답 검증 : 실시간 답변 생성
- 후처리 및 포맷팅

### 2.3.4 응답 검증 및 품질 관리

### 2.3.4.1 실시간 할루시네이션 검증 
- 사실 확인 및 인용 검증
- 신뢰도 계산 후 재생성 권고

### 2.3.4.2 응답 구조화 및 포맷팅
- 답변, 소스 목록, 면책 조항 포함

### 2.4 약관 관리
- 저장된 약관의 목록 제공
- 원본 파일 다운로드 및 삭제 기능
- PDF 파일 조회 기능
- Markdown 파일 조회 기능


## 3. 비기능 요건
- 웹 기반 UI(React, Open Web UI 스타일)
- 파일 및 데이터 보안
- 확장성 있는 DB 설계
- 빠른 검색 및 응답 속도


## 4. 시스템 아키텍처
- 챗 UI 기반 메인 화면(GPT 스타일)
- 좌측 탭(사이드바)에서 수동 기능 사용 가능
- React/Next.js(frontend) + FastAPI(backend) + PostgreSQL(pgvector)
- 로컬테스트 환경
- langgraph 워크플로우
  - User → Router → [Processing | Search + Answer | Management] → User

### 4.1 multi agent 구성 (LangGraph 기반):
- Router Agent (라우터):
  - 사용자 요청 분석 및 적절한 Agent로 라우팅
  - 입력: 사용자 질의
  - 출력: 의도 분류 (search/upload/manage)
- Processing Agent (전처리):
  - PDF 업로드 및 전처리 담당
  - Path 1 (직접 추출) + Path 2 (멀티모달) 병렬 실행
  - 결과 통합 및 품질 검증
- Search Agent (검색):
  - 벡터 검색 및 하이브리드 검색 수행
  - 컨텍스트 최적화
- Answer Agent (답변):
  - LLM 기반 답변 생성
  - 할루시네이션 검증
  - 응답 포맷팅 
- Management Agent (관리):
  - 약관 목록 조회, 삭제, 다운로드


## 5. 프론트엔드 화면 설계

- 대화 화면 (메인):
  - 최근 대화 (좌측)
  - 대화 영역 (중앙)
  - 참조 문서 패널 (우측, 토글 가능)
- 약관 관리 화면:
  - 업로드 버튼
  - 약관 목록 (테이블 뷰)
  - 필터/정렬 기능
- 검색 화면:
  - 검색 입력
  - 필터 옵션 (문서 선택, 기간 등)
  - 검색 결과 목록


## 6. 에러 처리
- 에러 처리:
  - 업로드 실패: 파일 형식 불일치, 용량 초과
  - 전처리 실패: PDF 손상, OCR 실패
  - 임베딩 실패: API 키 오류, 할당량 초과
  - 검색 실패: DB 연결 오류, 타임아웃
  
- 로깅 레벨:
  - INFO: 정상 처리 흐름
  - WARNING: 복구 가능한 오류
  - ERROR: 처리 실패
  - CRITICAL: 시스템 장애


## 7. 데이터베이스 테이블 설계(예시)

```sql

-- users (사용자 정보)
CREATE TABLE users (
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

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);


-- documents (문서 메타데이터)
CREATE TABLE documents (
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

CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_insurance_type ON documents(insurance_type);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_effective_date ON documents(effective_date);


CREATE EXTENSION IF NOT EXISTS vector;
-- document_chunks (벡터화된 청크)
CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_type VARCHAR(20) NOT NULL, -- 'text', 'table', 'image'
    page_number INTEGER,
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
CREATE INDEX idx_chunks_embedding ON document_chunks 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 32, ef_construction = 200);

-- 일반 인덱스
CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_chunks_type ON document_chunks(chunk_type);
CREATE INDEX idx_chunks_page ON document_chunks(page_number);
CREATE INDEX idx_chunks_clause ON document_chunks(clause_number);
CREATE INDEX idx_chunks_hash ON document_chunks(content_hash);


-- processing_logs (처리 로그)
CREATE TABLE processing_logs (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    processing_stage VARCHAR(50), -- 'extraction', 'chunking', 'embedding', 'indexing'
    status VARCHAR(20), -- 'started', 'completed', 'failed'
    message TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_processing_logs_document_id ON processing_logs(document_id);
CREATE INDEX idx_processing_logs_stage ON processing_logs(processing_stage);


-- search_logs (검색 로그)
CREATE TABLE search_logs (
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

CREATE INDEX idx_search_logs_user_id ON search_logs(user_id);
CREATE INDEX idx_search_logs_created_at ON search_logs(created_at);


```

## 8. 추가 참고사항
- PoC 단계이므로 동시 사용자 수, 대규모 트래픽 등은 우선 고려하지 않음
- UI/UX는 Open Web UI의 오픈소스 스타일을 참고하여 커스터마이징

---

*본 문서는 PoC(Proof of Concept) 단계의 요구사항 정의서로, 추후 상세 설계 및 구현 단계에서 변경될 수 있습니다.*
