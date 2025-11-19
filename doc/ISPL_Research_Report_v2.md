# 보험약관 기반 Agentic AI 시스템 - 기술 연구 보고서 v2

**작성일**: 2025년 10월 27일  
**프로젝트명**: ISPL (Insurance Policy) - Agentic AI System  
**버전**: 2.0 (실제 구현 기반 업데이트)

---

## 1. 프로젝트 개요

### 1.1 목적
- 생성형 AI를 활용하여 보험약관을 전처리, 요약, 임베딩 후 벡터DB에 저장
- 사용자의 자연어 질의에 대해 관련 약관을 검색하고 정확한 답변 제공
- 파일 업로드 및 약관 통합 관리 기능 제공
- Multi-Agent 시스템을 통한 지능형 워크플로우 구현

### 1.2 범위
- **약관 업로드 및 전처리**: PDF → 하이브리드 전처리 → Markdown → 임베딩 → 벡터DB 저장
- **약관 검색**: 사용자 질의 전처리 → 하이브리드 검색(벡터+키워드) → LLM 기반 답변 생성
- **약관 관리**: 저장된 약관 목록, 원본 파일 다운로드/삭제, PDF/Markdown 조회
- **대화 이력 관리**: 채팅 세션 관리 및 이력 조회

### 1.3 구현 현황
- PoC 단계 완료 (2025년 10월 27일 기준)
- 백엔드 및 프론트엔드 핵심 기능 구현 완료
- 7개 에이전트 기반 Multi-Agent 시스템 운영 중
- PostgreSQL + pgvector 기반 벡터 검색 구축 완료

### 1.4 제약 조건
- PoC 단계이므로 대규모 트래픽은 고려하지 않음
- 로컬 테스트 환경 우선
- 파일 형식: PDF만 지원

---

## 2. 기술 스택

### 2.1 Backend
- **Framework**: FastAPI 0.115.0 (Python)
- **AI Framework**: LangGraph 0.3.27+ (Multi-Agent 시스템)
- **Database**: PostgreSQL 17.6 + pgvector 0.3.6 extension
- **LLM**: OpenAI GPT-4o (gpt-4o)
- **Embedding**: OpenAI text-embedding-3-large (1536 차원)
- **PDF 처리**: 
  - PyMuPDF 1.24.14
  - pymupdf4llm 0.0.17
  - pdf2image 1.17.0
  - GPT-4o Vision
- **ORM**: SQLAlchemy 2.0.35 (비동기)
- **캐싱**: Redis 5.2.1 (선택사항, 미사용 시 MemoryCache 자동 대체)
- **한글 처리**: kiwipiepy 0.21.0

### 2.2 Frontend
- **Framework**: Next.js 15.0.3
- **UI Library**: React 18.3.1
- **Language**: TypeScript 5.6.3
- **Styling**: Tailwind CSS 3.4.14
- **Markdown**: react-markdown 9.0.1, remark-gfm 4.0.0

### 2.3 시스템 아키텍처

```
User → Frontend (Next.js)
         ↓
    FastAPI Backend
         ↓
   LangGraph Multi-Agent System
    ├─ Router Agent (라우팅)
    ├─ Search Agent (벡터+키워드 검색)
    ├─ Context Judgement Agent (컨텍스트 충분성 판단)
    ├─ Chunk Expansion Agent (청크 확장)
    ├─ Answer Agent (답변 생성 및 검증)
    ├─ Processing Agent (PDF 전처리)
    └─ Management Agent (약관 관리)
         ↓
  PostgreSQL + pgvector
```

---

## 3. LangGraph Multi-Agent 아키텍처 (실제 구현)

### 3.1 Agent 구성 (7개 에이전트)

**1. Router Agent (라우터)**
- 역할: 사용자 요청 분석 및 적절한 Agent로 라우팅
- 기술: LangGraph Command 객체 사용
- 의도 분류: search/upload/manage
- 위치: `backend/agents/router_agent.py`

**2. Search Agent (검색)**
- 역할: 하이브리드 검색 (벡터 + 키워드) 수행
- 검색 방식: 
  - 벡터 검색: Cosine Similarity 기반
  - 키워드 검색: PostgreSQL Full-Text Search (tsquery)
  - 결과 융합: Reciprocal Rank Fusion (RRF) 알고리즘
- 유사도 임계값: 0.7 이상
- 위치: `backend/agents/search_agent.py`

**3. Context Judgement Agent (컨텍스트 판단)**
- 역할: 검색된 컨텍스트가 답변 생성에 충분한지 판단
- 판단 기준:
  - 검색 결과 개수
  - 최고 유사도 점수
  - 컨텍스트 토큰 수
- 불충분 시 Chunk Expansion Agent로 라우팅
- 위치: `backend/agents/context_judgement_agent.py`

**4. Chunk Expansion Agent (청크 확장)**
- 역할: 컨텍스트가 불충분할 경우 관련 청크를 확장
- 확장 전략:
  - 인접 청크 가져오기 (이전/이후 청크)
  - 같은 섹션의 청크 추가
  - 최대 확장 횟수 제한
- 위치: `backend/agents/chunk_expansion_agent.py`

**5. Answer Agent (답변)**
- 역할: LLM 기반 답변 생성 및 검증
- 모델: GPT-4o (temperature: 0.1)
- 검증: AnswerValidator를 통한 다단계 검증
- 답변 형식: 구조화된 답변 (답변/관련 약관/주의사항)
- 위치: `backend/agents/answer_agent.py`

**6. Processing Agent (전처리)**
- 역할: PDF 업로드 및 하이브리드 전처리 담당
- 처리 방식: 
  - Path 1 (PyMuPDF4LLM) - 텍스트 직접 추출
  - Path 2 (GPT-4 Vision) - 이미지 기반 추출
  - Hybrid 병합 - 두 결과를 유사도 기반으로 병합
- 출력: 통합된 Markdown 문서 + 품질 검증 결과
- 위치: `backend/agents/processing_agent.py`

**7. Management Agent (관리)**
- 역할: 약관 목록 조회, 삭제, 다운로드
- 기능: CRUD 작업 전담
- 위치: `backend/agents/management_agent.py`

### 3.2 LangGraph 워크플로우

**검색 워크플로우**:
1. START → Router Agent
2. Router Agent → Search Agent (task_type="search")
3. Search Agent → Context Judgement Agent
4. Context Judgement Agent → 조건부 라우팅
   - 충분: Answer Agent
   - 불충분: Chunk Expansion Agent
5. Chunk Expansion Agent → Context Judgement Agent (재판단)
6. Answer Agent → END

**업로드 워크플로우**:
1. START → Router Agent
2. Router Agent → Processing Agent (task_type="upload")
3. Processing Agent → END

**관리 워크플로우**:
1. START → Router Agent
2. Router Agent → Management Agent (task_type="manage")
3. Management Agent → END

### 3.3 State 관리

**ISPLState 구조**:
- query: 사용자 질의
- messages: 메시지 이력
- next_agent: 다음 실행할 에이전트
- task_type: 작업 유형 (search/upload/manage)
- task_results: 각 에이전트의 실행 결과
- search_results: 검색 결과 리스트
- final_answer: 최종 답변
- error: 오류 정보
- context_sufficient: 컨텍스트 충분성 여부
- expanded_chunks: 확장된 청크 리스트
- expansion_count: 확장 횟수
- chunks_to_expand: 확장할 청크 리스트

---

## 4. 데이터베이스 스키마 (실제 구현)

### 4.1 테이블 구조

**users (사용자 정보)**
- id, username, email, full_name
- role (admin/user/agent)
- insurance_preferences (JSONB)
- created_at, last_login, is_active

**documents (문서 메타데이터)**
- id, filename, original_filename, file_path
- file_size, document_type, insurance_type
- company_name, version
- effective_date, expiry_date, status
- upload_timestamp, processed_timestamp
- total_pages, processing_status
- created_by, updated_at

**document_chunks (벡터화된 청크)**
- id, document_id, chunk_index
- chunk_type (text/table/image)
- page_number (Vision의 물리적 순서)
- pdf_page_number (PDF 내부 인쇄 페이지 번호)
- section_title, clause_number
- content, content_hash (SHA-256)
- token_count, metadata (JSONB)
- embedding (VECTOR(1536))
- confidence_score, created_at

**processing_logs (처리 로그)**
- id, document_id, processing_stage
- status, message, processing_time_ms
- created_at

**search_logs (검색 로그)**
- id, user_id, query, query_intent
- search_type, results_count
- top_similarity_score
- selected_document_ids
- response_time_ms, user_feedback
- created_at

**chat_sessions (채팅 세션)**
- id, user_id, title
- created_at, updated_at

**chat_messages (채팅 메시지)**
- id, session_id, role (user/assistant)
- content, metadata (JSONB)
- created_at

### 4.2 인덱스 전략

**HNSW 벡터 인덱스**:
- 인덱스명: idx_chunks_embedding
- 타입: HNSW (Hierarchical Navigable Small World)
- 연산자: vector_cosine_ops (Cosine Similarity)
- 파라미터: m=32, ef_construction=200

**일반 인덱스**:
- document_id, chunk_type, page_number
- pdf_page_number, clause_number, content_hash
- 각종 검색 및 조인 성능 최적화

**Full-Text Search**:
- 애플리케이션 레벨에서 tsquery 생성
- 키워드 기반 검색 지원

---

## 5. PDF 하이브리드 전처리 파이프라인 (실제 구현)

### 5.1 처리 흐름

```
PDF 입력
   ├─ Path 1: PyMuPDF4LLM (직접 텍스트 추출)
   │    ├─ PyMuPDF로 텍스트 추출
   │    └─ Markdown 변환
   │
   └─ Path 2: GPT-4 Vision (이미지 기반)
        ├─ pdf2image로 이미지 변환 (DPI 300)
        ├─ 이미지 전처리 (그레이스케일, 노이즈 제거)
        └─ GPT-4o Vision API 호출
   
결과 병합 (HybridMerger)
   ├─ 페이지별 정렬
   ├─ 유사도 기반 중복 감지
   └─ 최적 결과 선택
   ↓
품질 검증 (QualityValidator)
   ├─ 완전성 검사
   ├─ 일관성 검사
   └─ 정확도 추정
   ↓
청킹 (TextChunker)
   ├─ Fixed-size: 1000 토큰
   ├─ Overlap: 100 토큰
   └─ 특수 처리 (표/이미지)
   ↓
임베딩 생성 (EmbeddingService)
   ├─ 모델: text-embedding-3-large
   ├─ 차원: 1536
   └─ 배치 처리
   ↓
벡터 DB 저장 (AsyncSession)
```

### 5.2 처리 방식 선택

**pymupdf 모드**:
- PyMuPDF4LLM만 사용
- 빠른 처리 속도
- 텍스트 위주 문서에 적합

**vision 모드**:
- GPT-4 Vision만 사용
- 높은 정확도
- 복잡한 레이아웃/표/이미지가 많은 문서에 적합

**both 모드** (권장):
- 두 방식을 병행하여 최고 품질 보장
- PyMuPDF의 속도 + Vision의 정확도
- 하이브리드 병합으로 최적 결과 생성

### 5.3 주요 서비스 컴포넌트

**PDFProcessor** (`services/pdf_processor.py`):
- 전체 PDF 처리 오케스트레이션
- 방식 선택 및 실행
- Markdown 파일 저장
- 청킹 및 임베딩 통합

**PyMuPDFExtractor** (`services/pymupdf_extractor.py`):
- PyMuPDF4LLM을 사용한 직접 추출
- 빠른 텍스트 추출
- 기본 구조 인식

**VisionExtractor** (`services/vision_extractor.py`):
- pdf2image로 이미지 변환
- 이미지 전처리 (ImagePreprocessor)
- GPT-4o Vision API 호출
- 고품질 구조 분석

**HybridMerger** (`services/hybrid_merger.py`):
- 두 경로의 결과 병합
- SequenceMatcher 기반 유사도 계산
- 중복 제거 및 최적 선택

**QualityValidator** (`services/quality_validator.py`):
- 추출 품질 검증
- 완전성/일관성/정확도 평가
- 품질 점수 산출

**TextChunker** (`services/chunker.py`):
- Fixed-size 청킹 (1000 토큰)
- Overlap 처리 (100 토큰)
- 표/이미지 특수 처리

**EmbeddingService** (`services/embedding_service.py`):
- OpenAI API 호출
- 배치 처리
- 임베딩 캐싱 (EmbeddingCache)

---

## 6. 검색 시스템 (실제 구현)

### 6.1 Query 전처리

**QueryPreprocessor** (`services/query_preprocessor.py`):
- 공백 정규화
- 전문용어 표준화 (insurance_terms.json)
- 동의어 확장
- 조항 번호 추출
- 불완전 질의 감지
- 키워드 추출

**전문용어 사전** (`data/insurance_terms.json`):
- synonyms: 동의어 매핑
- normalization.spacing: 띄어쓰기 규칙
- incomplete_patterns: 불완전 질의 패턴

### 6.2 하이브리드 검색

**HybridSearchService** (`services/hybrid_search.py`):

**벡터 검색**:
- VectorSearchService 활용
- Cosine Similarity 기반
- HNSW 인덱스 사용
- 유사도 임계값: 0.7

**키워드 검색**:
- PostgreSQL tsquery 사용
- 키워드 추출 및 조사 제거
- AND 연산 (모든 키워드 포함)

**결과 융합 (RRF)**:
- Reciprocal Rank Fusion 알고리즘
- RRF_K = 60 (표준값)
- 벡터/키워드 검색 결과 융합

**컨텍스트 최적화**:
- 최대 토큰 수: 20,000 (GPT-4o)
- 토큰 카운팅: tiktoken (cl100k_base)
- 동적 청크 선택

### 6.3 청크 확장

**ChunkExpansionService** (`services/chunk_expansion_service.py`):
- 인접 청크 가져오기
- 같은 섹션 청크 추가
- 최대 확장 횟수 제한
- 토큰 제한 준수

**ChunkRepository** (`services/chunk_repository.py`):
- 청크 조회 및 관리
- 인접 청크 검색
- 섹션별 청크 조회

---

## 7. 답변 생성 및 검증 (실제 구현)

### 7.1 답변 생성

**AnswerAgent** (`agents/answer_agent.py`):
- GPT-4o 사용 (temperature: 0.1)
- 구조화된 프롬프트
- RAG (Retrieval-Augmented Generation) 패턴
- 실시간 검증

### 7.2 시스템 프롬프트

```
당신은 보험약관 전문 상담사입니다. 다음 규칙을 반드시 준수하세요:

1. 정확성 보장: 제공된 약관 내용에만 기반하여 답변하세요.
2. 근거 제시: 모든 답변에 해당 약관 조항을 인용하세요.
3. 한계 인정: 제공된 자료에 없는 내용은 "해당 정보가 약관에 명시되어 있지 않습니다"라고 답하세요.
4. 명확한 구조: 답변을 ①직접 답변 ②관련 약관 ③주의사항 순으로 구성하세요.
5. 금지사항: 추측, 일반 상식, 다른 보험사 정보는 절대 사용하지 마세요.
```

### 7.3 답변 검증 (4단계)

**AnswerValidator** (`services/answer_validator.py`):

**1. 형식 검증 (10%)**:
- 구조화 여부 확인
- 참조 번호 포함 확인
- 조항 번호 포함 확인

**2. 조항 검증 (20%)**:
- 언급된 조항 번호의 실제 존재 확인
- DB 조회를 통한 검증

**3. 컨텍스트 일치도 검증 (30%)**:
- 답변 내용이 제공된 컨텍스트에 기반하는지 확인
- 유사도 계산

**4. 할루시네이션 검증 (40%)**:
- GPT-4o를 사용한 사실 확인
- 생성된 답변을 원본 컨텍스트와 재대조
- 모순 감지

**최종 신뢰도 계산**:
- 가중 평균으로 최종 점수 산출
- 임계값: 0.7 (70점)
- 임계값 미달 시 재생성 권고

### 7.4 답변 구조

**📌 답변**:
- 직접적인 답변
- [참조 1], [참조 2] 형식으로 출처 표시

**📋 관련 약관**:
- [참조 1] 문서명 | 페이지 | 섹션 | 조항
- 관련 내용 요약

**⚠️ 주의사항**:
- 추가 확인 사항
- 제한 사항

---

## 8. 프론트엔드 구현 (실제 구현)

### 8.1 주요 화면

**메인 레이아웃** (`app/layout.tsx`, `components/AppLayout.tsx`):
- 좌측 사이드바 (채팅/문서/이력)
- 중앙 컨텐츠 영역
- 반응형 디자인

**채팅 화면** (`app/chat/page.tsx`):
- ChatInput: 질문 입력
- ChatMessage: 메시지 표시 (Markdown 지원)
- ReferencePanel: 참조 문서 패널 (토글)
- 실시간 스트리밍 지원

**문서 관리** (`app/documents/page.tsx`):
- DocumentUpload: 파일 업로드
- DocumentViewer: 문서 목록 및 상세
- 업로드/다운로드/삭제 기능

**대화 이력** (`app/history/page.tsx`):
- ChatHistory: 이전 대화 목록
- 세션별 관리

### 8.2 주요 컴포넌트

**Sidebar** (`components/Sidebar.tsx`):
- 네비게이션 메뉴
- 아이콘 기반 UI

**ChatInput** (`components/ChatInput.tsx`):
- 텍스트 입력
- 전송 버튼
- 엔터키 지원

**ChatMessage** (`components/ChatMessage.tsx`):
- 사용자/AI 메시지 구분
- Markdown 렌더링 (react-markdown)
- 코드 하이라이팅

**ReferencePanel** (`components/ReferencePanel.tsx`):
- 참조 문서 표시
- 페이지/섹션 정보
- 유사도 점수

### 8.3 API 통신

**API Client** (`lib/api.ts`):
- fetch 기반 API 호출
- 타입 안전성 (TypeScript)
- 에러 처리

**주요 엔드포인트**:
- POST /api/chat/stream: 스트리밍 채팅
- POST /api/chat/sessions: 세션 생성
- GET /api/documents: 문서 목록
- POST /api/documents/upload: 문서 업로드
- DELETE /api/documents/{id}: 문서 삭제

---

## 9. API 엔드포인트 (실제 구현)

### 9.1 채팅 API (`api/chat.py`)

**POST /api/chat/stream**:
- 스트리밍 방식 채팅
- Server-Sent Events (SSE)
- 실시간 답변 생성

**POST /api/chat/sessions**:
- 새 채팅 세션 생성

**GET /api/chat/sessions**:
- 채팅 세션 목록 조회

**GET /api/chat/sessions/{session_id}/messages**:
- 특정 세션의 메시지 조회

### 9.2 문서 API (`api/documents.py`)

**GET /api/documents**:
- 문서 목록 조회
- 필터링 지원

**POST /api/documents/upload**:
- PDF 파일 업로드
- 멀티파트 폼 데이터
- 비동기 처리

**DELETE /api/documents/{document_id}**:
- 문서 삭제 (CASCADE)

**GET /api/documents/{document_id}/download**:
- 원본 파일 다운로드

### 9.3 검색 API (`api/search.py`)

**POST /api/search**:
- 하이브리드 검색
- 필터 지원 (문서 타입, 조항 번호 등)

### 9.4 PDF API (`api/pdf.py`)

**POST /api/pdf/process**:
- PDF 전처리 트리거
- 방식 선택 (pymupdf/vision/both)

### 9.5 채팅 이력 API (`api/chat_history.py`)

**GET /api/chat/history**:
- 전체 대화 이력 조회

### 9.6 Health Check (`api/health.py`)

**GET /api/health**:
- 서비스 상태 확인
- DB 연결 상태
- OpenAI API 상태

---

## 10. 핵심 기술 및 최적화

### 10.1 비동기 처리

**AsyncIO 활용**:
- FastAPI의 비동기 엔드포인트
- SQLAlchemy AsyncSession
- OpenAI AsyncClient
- 동시성 향상

### 10.2 캐싱 전략

**EmbeddingCache** (`services/embedding_cache.py`):
- 임베딩 결과 캐싱 (MemoryCache 사용)
- content_hash를 키로 사용
- 중복 API 호출 방지
- 비용 절감

**일반 캐싱** (`core/cache.py`):
- CacheFacade 패턴: Redis 시도 → 실패 시 MemoryCache 자동 대체
- 검색 결과 캐싱
- TTL 설정
- LRU 메모리 관리 (max_size=10000)

### 10.3 성능 최적화

**HNSW 인덱스**:
- 빠른 근사 최근접 이웃 검색
- m=32, ef_construction=200
- Cosine Similarity 최적화

**Connection Pooling**:
- SQLAlchemy 연결 풀
- 재사용을 통한 성능 향상

**배치 처리**:
- 임베딩 배치 생성
- 벡터 검색 최적화

### 10.4 토큰 관리

**tiktoken 활용**:
- 정확한 토큰 카운팅
- cl100k_base 인코딩 (GPT-4 호환)
- 컨텍스트 최적화
- 비용 예측

### 10.5 에러 처리

**계층적 에러 처리**:
- Try-except 블록
- 에러 로깅
- 사용자 친화적 메시지
- 재시도 로직 (tenacity)

**로깅 레벨**:
- INFO: 정상 흐름
- WARNING: 복구 가능한 오류
- ERROR: 처리 실패
- CRITICAL: 시스템 장애

---

## 11. 보안 및 데이터 관리

### 11.1 환경 변수 관리

**Settings** (`core/config.py`):
- pydantic-settings 사용
- .env 파일 로딩
- 타입 검증
- 기본값 설정

**주요 설정**:
- DATABASE_URL
- OPENAI_API_KEY
- REDIS_URL (선택)
- UPLOAD_DIR
- MAX_UPLOAD_SIZE

### 11.2 파일 관리

**업로드 디렉토리 구조**:
```
uploads/
  ├── documents/          # 원본 PDF + Markdown
  │   ├── {filename}_{document_id}.pdf
  │   └── {filename}_{document_id}.md
  ├── images/            # 추출된 이미지
  │   └── {document_id}/
  │       └── page_{n}_img_{m}.png
  └── temp/              # 임시 파일
```

**파일명 규칙**:
- document_id 포함
- 고유성 보장
- 타임스탬프 선택 사용

### 11.3 데이터 무결성

**CASCADE 삭제**:
- documents 삭제 시 관련 chunks 자동 삭제
- 로컬 파일도 함께 삭제

**트랜잭션 관리**:
- AsyncSession 사용
- 원자성 보장
- 롤백 지원

---

## 12. 할루시네이션 방지 전략 (실제 구현)

### 12.1 프롬프트 엔지니어링

**엄격한 규칙 명시**:
- 제공된 컨텍스트만 사용
- 근거 반드시 제시
- 모를 경우 명시적 표현
- 추측 금지

**구조화된 출력**:
- 일관된 형식 강제
- 참조 번호 매핑
- 출처 추적 가능

### 12.2 다단계 검증

**실시간 검증**:
- 답변 생성 직후 검증
- 4단계 검증 프로세스
- 가중치 기반 점수 계산

**재생성 로직**:
- 임계값(0.7) 미달 시 재생성
- 최대 재시도 횟수 제한
- 사용자에게 경고 표시

### 12.3 컨텍스트 관리

**충분성 판단**:
- Context Judgement Agent
- 자동 청크 확장
- 토큰 제한 준수

**관련성 보장**:
- 높은 유사도 임계값 (0.7)
- 하이브리드 검색
- 키워드 매칭

---

## 13. 테스트 전략 (실제 구현)

### 13.1 테스트 파일 구조

**backend/test/** 디렉토리:
- 30+ 테스트 파일
- 단위 테스트 및 통합 테스트
- E2E 테스트

### 13.2 주요 테스트 영역

**Agent 테스트**:
- test_langgraph_agents.py
- test_3_agent_structure.py
- test_search_agent_*.py
- test_answer_agent_*.py

**검색 테스트**:
- test_vector_search.py
- test_keyword_search.py
- test_hybrid_search_integration.py
- test_rrf_and_context.py

**전처리 테스트**:
- test_pdf_processing.py
- test_vision_extraction.py
- test_chunking.py
- test_query_preprocessor_*.py

**검증 테스트**:
- test_answer_validation_*.py
- test_answer_validator_*.py
- test_hallucination_prevention.py

**통합 테스트**:
- test_api_integration.py
- test_answer_validation_e2e.py

---

## 14. 기술적 도전과 해결 방법

### 14.1 PDF 처리 품질

**도전**:
- 복잡한 레이아웃
- 표 인식 오류
- 이미지 내 텍스트

**해결**:
- 하이브리드 전처리 (PyMuPDF + Vision)
- 유사도 기반 병합
- 품질 검증 단계

### 14.2 검색 정확도

**도전**:
- 의미 기반 검색의 한계
- 전문용어 미스매치
- 컨텍스트 부족

**해결**:
- 하이브리드 검색 (벡터 + 키워드)
- Query 전처리 및 표준화
- 동적 청크 확장

### 14.3 할루시네이션

**도전**:
- LLM의 환각 현상
- 근거 없는 답변
- 정보 혼동

**해결**:
- 엄격한 프롬프트
- 4단계 검증 프로세스
- 실시간 재대조

### 14.4 성능 최적화

**도전**:
- 벡터 검색 속도
- API 호출 비용
- 메모리 사용량

**해결**:
- HNSW 인덱스
- 임베딩 캐싱
- 비동기 처리
- 배치 최적화

### 14.5 페이지 번호 처리

**도전**:
- Vision의 물리적 순서 vs PDF 인쇄 페이지
- 페이지 번호 불일치

**해결**:
- 이중 페이지 번호 시스템
- page_number (물리적)
- pdf_page_number (인쇄)
- 별도 컬럼 관리

---

## 15. 향후 개선 방향

### 15.1 단기 개선 (1-2개월)

**1. 사용자 인증**:
- 로그인/회원가입
- 세션 관리
- 권한 관리

**2. 문서 버전 관리**:
- 약관 개정 이력
- 버전별 비교
- 유효 기간 관리

**3. 고급 검색 필터**:
- 날짜 범위
- 보험 유형
- 회사별

**4. 피드백 시스템**:
- 답변 평가
- 개선 학습
- 품질 모니터링

### 15.2 중기 개선 (3-6개월)

**1. 다중 파일 형식 지원**:
- Word 문서
- Excel 스프레드시트
- HTML

**2. 약관 비교 기능**:
- 여러 보험사 비교
- 차이점 분석
- 시각화

**3. 자동 요약**:
- 주요 내용 요약
- 핵심 조항 추출
- 요약 카드

**4. 대화형 개선**:
- 다중 턴 대화
- 컨텍스트 유지
- 추가 질문

### 15.3 장기 개선 (6개월+)

**1. Fine-tuning**:
- 도메인 특화 모델
- 보험 전문 LLM
- 성능 향상

**2. 멀티모달 확장**:
- 음성 인터페이스
- 이미지 검색
- 동영상 설명

**3. 실시간 업데이트**:
- 약관 변경 알림
- 자동 재처리
- 증분 업데이트

**4. 고급 분석**:
- 사용 패턴 분석
- 인기 질문
- 대시보드

---

## 16. 기술적 위험 요소 및 대응 방안

| 위험 요소 | 영향도 | 발생 가능성 | 현재 상태 | 대응 방안 |
|---------|-------|-----------|---------|---------|
| PDF 전처리 품질 저하 | 높음 | 중간 | ✅ 해결 | 하이브리드 방식, 품질 검증 단계 |
| LLM 할루시네이션 | 높음 | 높음 | ✅ 완화 | 4단계 검증, 재생성 로직 |
| 벡터 검색 성능 저하 | 중간 | 중간 | ✅ 최적화 | HNSW 인덱스, 캐싱 |
| OpenAI API 비용 | 중간 | 높음 | ⚠️ 모니터링 | 임베딩 캐싱, 배치 처리 |
| Multi-Agent 복잡도 | 중간 | 중간 | ✅ 관리 | 명확한 책임 분리, 테스트 |
| DB 병목 현상 | 낮음 | 낮음 | ✅ 예방 | 인덱싱, Connection Pool |
| 파일 스토리지 용량 | 낮음 | 중간 | ⚠️ 주시 | 정기 정리, 압축 |

---

## 17. 성능 지표 (예상)

### 17.1 처리 속도

**PDF 처리**:
- PyMuPDF 모드: ~5-10초 (10페이지 기준)
- Vision 모드: ~30-60초 (10페이지 기준)
- Hybrid 모드: ~40-70초 (10페이지 기준)

**검색 속도**:
- 벡터 검색: ~100-300ms
- 키워드 검색: ~50-150ms
- 하이브리드 검색: ~200-500ms

**답변 생성**:
- GPT-4o 호출: ~2-5초
- 검증 포함: ~3-7초

### 17.2 정확도

**검색 정확도**:
- 벡터 검색: ~75-85%
- 하이브리드 검색: ~85-95%

**답변 품질**:
- 신뢰도 평균: ~0.8-0.9
- 할루시네이션 방지율: ~90-95%

### 17.3 비용 (OpenAI API)

**임베딩**:
- text-embedding-3-large: $0.13 / 1M tokens
- 10페이지 문서: ~$0.01-0.05

**답변 생성**:
- GPT-4o: Input $2.5 / 1M tokens, Output $10 / 1M tokens
- 1회 답변: ~$0.02-0.10

**Vision**:
- GPT-4o Vision: ~$0.01-0.05 / 페이지

---

## 18. 실제 구현된 주요 파일 목록

### 18.1 Backend

**핵심 파일**:
- `main.py`: FastAPI 애플리케이션 진입점
- `core/config.py`: 설정 관리
- `core/database.py`: DB 연결
- `core/cache.py`: Redis 캐싱

**Agents** (7개):
- `agents/graph.py`: LangGraph 정의
- `agents/state.py`: State 정의
- `agents/router_agent.py`
- `agents/search_agent.py`
- `agents/context_judgement_agent.py`
- `agents/chunk_expansion_agent.py`
- `agents/answer_agent.py`
- `agents/processing_agent.py`
- `agents/management_agent.py`

**Services** (18개):
- `services/pdf_processor.py`
- `services/pymupdf_extractor.py`
- `services/vision_extractor.py`
- `services/hybrid_merger.py`
- `services/quality_validator.py`
- `services/chunker.py`
- `services/embedding_service.py`
- `services/embedding_cache.py`
- `services/vector_search.py`
- `services/hybrid_search.py`
- `services/query_preprocessor.py`
- `services/answer_validator.py`
- `services/chunk_expansion_service.py`
- `services/chunk_repository.py`
- `services/reranker.py`
- `services/image_preprocessor.py`
- `services/structure_analyzer.py`
- `services/service_container.py`

**API** (6개):
- `api/chat.py`
- `api/documents.py`
- `api/search.py`
- `api/pdf.py`
- `api/chat_history.py`
- `api/health.py`

**Models** (7개):
- `models/document.py`
- `models/document_chunk.py`
- `models/preprocessed_query.py`
- `models/search_log.py`
- `models/answer_validation.py`
- `models/chat_session.py`
- `models/chat_message.py`

**Database**:
- `database/schema.sql`
- `database/init_db.py`
- `database/migrations/`

### 18.2 Frontend

**Pages** (4개):
- `app/page.tsx`: 홈
- `app/chat/page.tsx`: 채팅
- `app/documents/page.tsx`: 문서 관리
- `app/history/page.tsx`: 대화 이력

**Components** (10개):
- `components/AppLayout.tsx`
- `components/Sidebar.tsx`
- `components/ChatInput.tsx`
- `components/ChatMessage.tsx`
- `components/ChatHistory.tsx`
- `components/ReferencePanel.tsx`
- `components/DocumentUpload.tsx`
- `components/DocumentViewer.tsx`
- `components/UploadModal.tsx`
- `components/DeleteConfirmDialog.tsx`

**Library**:
- `lib/api.ts`: API 클라이언트

---

## 19. 권장 라이브러리 버전 (실제 사용)

### Backend
```
fastapi==0.115.0
uvicorn[standard]==0.32.0
sqlalchemy==2.0.35
asyncpg==0.30.0
pgvector==0.3.6
pymupdf==1.24.14
pymupdf4llm==0.0.17
pdf2image==1.17.0
openai==1.55.3
langgraph>=0.3.27
langchain==0.3.7
langchain-openai==0.2.8
pydantic==2.10.2
redis[hiredis]==5.2.1
tiktoken==0.8.0
tenacity==9.0.0
kiwipiepy==0.21.0
Pillow==11.0.0
opencv-python==4.10.0.84
numpy>=1.26.0,<2.0.0
```

### Frontend
```
next==15.0.3
react==18.3.1
typescript==5.6.3
tailwindcss==3.4.14
react-markdown==9.0.1
remark-gfm==4.0.0
```

---

## 20. 결론

### 20.1 구현 성과

본 프로젝트는 보험약관 기반 Agentic AI 시스템의 PoC를 성공적으로 구축했습니다.

**핵심 성공 요소**:

1. **LangGraph Multi-Agent 시스템**
   - 7개 에이전트의 유연한 협업
   - 명확한 책임 분리
   - 확장 가능한 아키텍처

2. **하이브리드 PDF 전처리**
   - PyMuPDF의 속도 + Vision의 정확도
   - 품질 검증 단계
   - 높은 텍스트 추출 품질

3. **하이브리드 검색 시스템**
   - 벡터 검색 + 키워드 검색
   - RRF 융합 알고리즘
   - 동적 청크 확장

4. **다단계 답변 검증**
   - 4단계 검증 프로세스
   - 할루시네이션 방지
   - 높은 답변 신뢰도

5. **현대적 기술 스택**
   - FastAPI + SQLAlchemy (비동기)
   - Next.js 15 + React 18
   - PostgreSQL + pgvector
   - OpenAI GPT-4o

### 20.2 학습 내용

**기술적 학습**:
- LangGraph의 Multi-Agent 패턴
- 하이브리드 검색 및 RAG 구현
- 비동기 Python 프로그래밍
- pgvector 벡터 검색 최적화

**도메인 학습**:
- 보험약관 구조 이해
- 전문용어 표준화
- 할루시네이션 방지 전략
- 검증 프로세스 설계

### 20.3 다음 단계

**즉시 가능**:
- 사용자 피드백 수집
- 성능 모니터링
- 비용 최적화
- 테스트 커버리지 확대

**단기 목표** (1-2개월):
- 사용자 인증 추가
- 문서 버전 관리
- 고급 필터링
- 피드백 시스템

**장기 비전** (6개월+):
- 도메인 특화 모델 Fine-tuning
- 멀티모달 확장
- 실시간 약관 업데이트
- 대규모 서비스 전환

### 20.4 최종 평가

ISPL 프로젝트는 생성형 AI와 전통적인 검색 기술을 성공적으로 결합하여, 실용적이고 정확한 보험약관 질의응답 시스템을 구축했습니다. Multi-Agent 아키텍처는 복잡한 워크플로우를 효과적으로 관리하며, 엄격한 검증 프로세스는 높은 답변 품질을 보장합니다.

PoC 단계를 넘어 실제 서비스로 발전시키기 위한 기술적 기반이 충분히 마련되었으며, 향후 개선을 통해 더욱 강력한 AI 기반 보험 상담 플랫폼으로 성장할 수 있을 것입니다.

---

**문서 버전**: 2.0  
**최종 업데이트**: 2025년 10월 27일  
**작성자**: ISPL 개발팀

