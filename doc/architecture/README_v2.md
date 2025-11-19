# ISPL 아키텍처 다이어그램 v2

보험 약관 기반 AI 챗봇 서비스의 시스템 아키텍처를 시각화한 다이어그램 모음입니다.  
**버전 2.0**: 실제 구현된 시스템을 반영하여 업데이트 (2025-10-27)

---

## 📊 다이어그램 목록

### 1. 시스템 개요 (01_system_overview_v2.svg)
전체 시스템의 구성 요소와 데이터 흐름을 한눈에 보여줍니다.

**주요 구성 요소**:
- 사용자 인터페이스 (Next.js 15 + React 18)
- API 서버 (FastAPI 0.115.0)
- LangGraph 멀티 에이전트 시스템 (7개 에이전트)
- PostgreSQL 17.6 + pgvector 0.3.6
- OpenAI API 통합 (GPT-4o, text-embedding-3-large)
- 캐싱 (MemoryCache 기본, Redis 선택사항)

**데이터 흐름**:
1. 사용자 → Frontend (Next.js)
2. Frontend → Backend API (FastAPI)
3. Backend → LangGraph Multi-Agent System
4. Agents → PostgreSQL + pgvector
5. Agents → OpenAI API
6. Response → User

---

### 2. LangGraph 멀티 에이전트 v2 (02_langgraph_agents_v2.svg)
LangGraph 기반 멀티 에이전트 시스템의 구조와 라우팅 로직을 상세히 설명합니다.

**에이전트 구성 (7개)**:

1. **Router Agent** (라우터)
   - 역할: 사용자 의도 분석 및 작업 라우팅
   - 출력: task_type (search/upload/manage)
   - 라우팅: Command 객체 사용

2. **Search Agent** (검색)
   - 역할: 하이브리드 검색 (벡터 + 키워드)
   - 기술: RRF 융합, 유사도 임계값 0.7
   - 출력: search_results

3. **Context Judgement Agent** (컨텍스트 판단) ⭐ NEW
   - 역할: 검색된 컨텍스트 충분성 판단
   - 기준: 결과 개수, 유사도, 토큰 수
   - 출력: context_sufficient (True/False)

4. **Chunk Expansion Agent** (청크 확장) ⭐ NEW
   - 역할: 컨텍스트 부족 시 관련 청크 확장
   - 전략: 인접 청크, 같은 섹션 청크
   - 제한: 최대 확장 횟수, 토큰 제한

5. **Answer Agent** (답변)
   - 역할: RAG 기반 답변 생성 및 4단계 검증
   - 모델: GPT-4o (temperature: 0.1)
   - 검증: 형식/조항/컨텍스트/할루시네이션

6. **Processing Agent** (전처리)
   - 역할: PDF 하이브리드 전처리
   - 방식: PyMuPDF + Vision → 병합
   - 출력: Markdown + 품질 검증

7. **Management Agent** (관리)
   - 역할: 약관 CRUD 작업
   - 기능: 목록/조회/삭제/다운로드

**상태 관리 (ISPLState)**:
- query, messages, next_agent
- task_type, task_results
- search_results, final_answer
- context_sufficient, expanded_chunks
- expansion_count, chunks_to_expand
- error

**워크플로우**:

*검색 플로우*:
```
START → Router → Search Agent → Context Judgement Agent
                                        ↓
                     ┌─────────────────┴──────────────┐
                     ↓                                ↓
              context_sufficient=True      context_sufficient=False
                     ↓                                ↓
              Answer Agent                  Chunk Expansion Agent
                     ↓                                ↓
                    END                Context Judgement Agent (재판단)
```

*업로드 플로우*:
```
START → Router → Processing Agent → END
```

*관리 플로우*:
```
START → Router → Management Agent → END
```

---

### 3. PDF 처리 파이프라인 v2 (03_pdf_processing_pipeline_v2.svg)
PDF 업로드부터 벡터 임베딩까지의 하이브리드 전처리 파이프라인을 설명합니다.

**처리 단계**:

1. **PDF 업로드**
   - 사용자가 보험 약관 PDF 업로드
   - 파일 검증 및 저장

2. **Path 1: PyMuPDF4LLM** (직접 텍스트 추출)
   - PyMuPDF로 텍스트 추출
   - Markdown 변환
   - 빠른 처리 (10페이지 ~5-10초)

3. **Path 2: GPT-4o Vision** (이미지 기반)
   - pdf2image로 고해상도 이미지 변환 (DPI 300)
   - 이미지 전처리 (그레이스케일, 노이즈 제거)
   - GPT-4o Vision API 호출
   - 고품질 구조 분석 (10페이지 ~30-60초)

4. **Hybrid Merging** (결과 병합)
   - HybridMerger 서비스
   - 페이지별 정렬
   - SequenceMatcher 기반 유사도 계산
   - 중복 제거 및 최적 결과 선택

5. **Quality Validation** (품질 검증)
   - QualityValidator 서비스
   - 완전성 검사 (블록 수 대비 점수)
   - 일관성 검사 (중복 여부)
   - 정확도 추정 (신뢰도 평균)

6. **Chunking** (청킹)
   - TextChunker 서비스
   - Fixed-size: 1000 토큰
   - Overlap: 100 토큰
   - 특수 처리: 표(전체 단위), 이미지(200-400 토큰)

7. **Embedding** (임베딩 생성)
   - EmbeddingService
   - 모델: text-embedding-3-large
   - 차원: 1536
   - 배치 처리
   - EmbeddingCache (MemoryCache)

8. **Storage** (벡터 DB 저장)
   - PostgreSQL + pgvector
   - document_chunks 테이블
   - HNSW 인덱스 (m=32, ef_construction=200)

**파일 저장 구조**:
```
uploads/
  ├── documents/
  │   ├── {filename}_{document_id}.pdf
  │   └── {filename}_{document_id}.md
  ├── images/
  │   └── {document_id}/
  │       └── page_{n}_img_{m}.png
  └── temp/
```

---

### 4. 검색 및 답변 플로우 v2 (04_search_answer_flow_v2.svg)
사용자 질문부터 최종 답변까지의 전체 검색 및 생성 과정을 설명합니다.

**플로우**:

1. **사용자 질문**
   - 자연어 질문 입력
   - Frontend (ChatInput 컴포넌트)

2. **의도 분석**
   - Router Agent가 질문 유형 분류
   - task_type 결정 (search/upload/manage)

3. **Query 전처리** ⭐ ENHANCED
   - QueryPreprocessor 서비스
   - 공백 정규화
   - 전문용어 표준화 (insurance_terms.json)
   - 동의어 확장
   - 조항 번호 추출
   - 키워드 추출

4. **하이브리드 검색** ⭐ ENHANCED
   - HybridSearchService
   - **벡터 검색**:
     - Query 임베딩 생성
     - pgvector로 유사 청크 검색
     - Cosine Similarity
     - HNSW 인덱스 사용
   - **키워드 검색**:
     - PostgreSQL Full-Text Search
     - tsquery 생성 (조사 제거)
     - AND 연산
   - **RRF 융합**:
     - Reciprocal Rank Fusion (K=60)
     - 벡터/키워드 결과 융합

5. **컨텍스트 판단** ⭐ NEW
   - Context Judgement Agent
   - 충분성 평가
   - 불충분 시 → Chunk Expansion Agent

6. **청크 확장** (필요 시) ⭐ NEW
   - Chunk Expansion Agent
   - 인접 청크 가져오기
   - 같은 섹션 청크 추가
   - 최대 확장 제한
   - 재판단 루프

7. **컨텍스트 최적화**
   - 최대 토큰: 20,000 (GPT-4o)
   - tiktoken으로 토큰 카운팅
   - 동적 청크 선택

8. **답변 생성**
   - Answer Agent
   - GPT-4o (temperature: 0.1)
   - RAG (Retrieval-Augmented Generation)
   - 구조화된 프롬프트

9. **4단계 검증** ⭐ ENHANCED
   - AnswerValidator 서비스
   - **형식 검증** (10%): 구조/참조/조항 포함
   - **조항 검증** (20%): DB 조회로 실제 존재 확인
   - **컨텍스트 일치도** (30%): 유사도 계산
   - **할루시네이션 검증** (40%): GPT-4o로 사실 확인
   - 최종 신뢰도 계산 (가중 평균)
   - 임계값: 0.7 (미달 시 재생성)

10. **응답 반환**
    - 구조화된 답변:
      - 📌 답변 (참조 번호 포함)
      - 📋 관련 약관 (출처 명시)
      - ⚠️ 주의사항
    - Frontend (ChatMessage 컴포넌트)
    - Markdown 렌더링

---

### 5. 데이터베이스 스키마 v2 (05_database_schema_v2.svg)
PostgreSQL 데이터베이스의 테이블 구조와 관계를 보여줍니다.

**주요 테이블**:

**users** (사용자 정보)
- id, username, email, full_name
- role (admin/user/agent)
- insurance_preferences (JSONB)
- created_at, last_login, is_active

**documents** (문서 메타데이터)
- id, filename, original_filename, file_path
- file_size, document_type, insurance_type
- company_name, version
- effective_date, expiry_date, status
- upload_timestamp, processed_timestamp
- total_pages, processing_status
- created_by, updated_at

**document_chunks** (벡터화된 청크) ⭐ UPDATED
- id, document_id, chunk_index
- chunk_type (text/table/image)
- **page_number** (Vision의 물리적 순서) ⭐ ENHANCED
- **pdf_page_number** (PDF 내부 인쇄 페이지) ⭐ NEW
- section_title, clause_number
- content, content_hash (SHA-256)
- token_count, metadata (JSONB)
- **embedding** (VECTOR(1536))
- confidence_score, created_at

**processing_logs** (처리 로그)
- id, document_id, processing_stage
- status, message, processing_time_ms
- created_at

**search_logs** (검색 로그)
- id, user_id, query, query_intent
- search_type (vector/keyword/hybrid)
- results_count, top_similarity_score
- selected_document_ids (배열)
- response_time_ms, user_feedback
- created_at

**chat_sessions** (채팅 세션) ⭐ NEW
- id, user_id, title
- created_at, updated_at

**chat_messages** (채팅 메시지) ⭐ NEW
- id, session_id, role (user/assistant)
- content, metadata (JSONB)
- created_at

**관계**:
- documents ← document_chunks (1:N, CASCADE)
- documents ← processing_logs (1:N)
- users ← search_logs (1:N)
- users ← chat_sessions (1:N)
- chat_sessions ← chat_messages (1:N, CASCADE)

**인덱스**:

*HNSW 벡터 인덱스*:
```sql
CREATE INDEX idx_chunks_embedding ON document_chunks 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 32, ef_construction = 200);
```

*일반 인덱스*:
- document_id, chunk_type, page_number
- pdf_page_number ⭐ NEW
- clause_number, content_hash
- 각종 외래키 및 검색 필드

*Full-Text Search*:
- 애플리케이션 레벨에서 tsquery 생성
- 키워드 기반 검색 지원

---

### 6. 기술 스택 v2 (06_tech_stack_v2.svg)
프로젝트에서 사용하는 모든 기술 스택을 카테고리별로 정리합니다.

**Frontend**:
- Next.js **15.0.3** (App Router) ⭐ UPDATED
- React **18.3.1**
- TypeScript **5.6.3** ⭐ UPDATED
- Tailwind CSS **3.4.14** ⭐ UPDATED
- react-markdown **9.0.1** ⭐ NEW
- remark-gfm **4.0.0** ⭐ NEW

**Backend**:
- FastAPI **0.115.0** ⭐ UPDATED
- Python **3.11+**
- Pydantic **2.10.2** ⭐ UPDATED
- SQLAlchemy **2.0.35** (비동기) ⭐ UPDATED
- LangGraph **0.3.27+** ⭐ UPDATED
- uvicorn **0.32.0** ⭐ UPDATED

**AI/ML**:
- OpenAI **GPT-4o** (gpt-4o) ⭐ UPDATED
- GPT-4o Vision ⭐ UPDATED
- text-embedding-3-large (1536차원)
- LangChain **0.3.7** ⭐ UPDATED
- langchain-openai **0.2.8** ⭐ UPDATED
- OpenAI SDK **1.55.3** ⭐ UPDATED

**Data Processing**:
- PyMuPDF **1.24.14** ⭐ UPDATED
- pymupdf4llm **0.0.17** ⭐ UPDATED
- pdf2image **1.17.0**
- OpenCV **4.10.0.84** ⭐ UPDATED
- Pillow **11.0.0** ⭐ UPDATED
- kiwipiepy **0.21.0** (한글 형태소 분석) ⭐ NEW
- tiktoken **0.8.0** ⭐ UPDATED
- tenacity **9.0.0** (재시도 로직) ⭐ NEW

**Database**:
- PostgreSQL **17.6** ⭐ UPDATED
- pgvector **0.3.6** ⭐ UPDATED
- asyncpg **0.30.0** ⭐ UPDATED
- HNSW 인덱스
- Cosine Similarity
- Full-Text Search (tsquery)
- Connection Pooling

**Cache & Storage**:
- MemoryCache (LRU, 10K) - 기본 사용
- Redis **5.2.1** (선택사항, 미사용) ⭐ UPDATED
- 로컬 파일 시스템 (uploads/)

**Development**:
- python-multipart **0.0.12**
- python-dotenv **1.0.1** ⭐ UPDATED
- pydantic-settings **2.6.1** ⭐ UPDATED

**Infrastructure**:
- 로컬 개발 환경 (Windows/Mac/Linux)
- PostgreSQL Server
- Redis Server (선택사항, 미설정 시 MemoryCache 자동 사용)
- Poppler (pdf2image 의존성)

---

## 🎨 다이어그램 특징

### 색상 코드
- **파란색** (#4A90E2): Frontend / 입력 / 사용자
- **주황색** (#F5A623): Backend / API
- **보라색** (#BD10E0): AI/ML / LLM
- **녹색** (#7ED321): 데이터 처리
- **청록색** (#50E3C2): 데이터베이스
- **회색** (#9B9B9B): 인프라
- **빨간색** (#D0021B): 경고/중요

### 아이콘
- 📄 PDF 문서
- 🔍 검색
- 🤖 AI 에이전트
- 💾 데이터베이스
- ⚡ API
- 📊 분석
- 🔒 보안
- ⭐ 신규/업데이트

---

## 📖 사용 방법

### 1. 브라우저에서 보기
`viewer_v2.html` 파일을 브라우저로 열면 모든 v2 다이어그램을 한 화면에서 볼 수 있습니다.

### 2. 개별 SVG 파일 보기
각 `*_v2.svg` 파일을 직접 브라우저나 SVG 뷰어로 열 수 있습니다.

### 3. 문서에 포함
Markdown이나 HTML 문서에 이미지로 포함할 수 있습니다.

```markdown
![시스템 개요](./architecture/01_system_overview_v2.svg)
```

---

## 🔧 다이어그램 수정

SVG 파일은 텍스트 에디터로 직접 수정 가능합니다. 각 파일은 다음 구조로 되어 있습니다:

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800">
  <defs>
    <style>
      /* CSS 스타일 정의 */
    </style>
  </defs>
  
  <!-- SVG 요소들 -->
</svg>
```

---

## 📚 참고 문서

- [PRD 문서](../Insurance%20Policy_prd.md)
- [연구 보고서 v2](../ISPL_Research_Report_v2.md) ⭐ NEW
- [연구 보고서 v1](../ISPL_Research_Report.md)
- [작업 계획 v2](../ISPL_Task_Plan_v2.md)

---

## 🆕 v2 주요 변경사항

### 2025-10-27: v2 업데이트
- 실제 구현된 시스템을 반영하여 전면 업데이트
- 7개 에이전트 시스템 반영 (기존 5개 → 7개)
  - Context Judgement Agent 추가
  - Chunk Expansion Agent 추가
- 하이브리드 검색 시스템 상세화
  - RRF 융합 알고리즘
  - Query 전처리
  - 동적 청크 확장
- 4단계 답변 검증 프로세스 추가
- 데이터베이스 스키마 업데이트
  - chat_sessions, chat_messages 테이블 추가
  - pdf_page_number 필드 추가
- 기술 스택 실제 버전 반영
- 성능 지표 및 워크플로우 상세화

---

## ✅ 업데이트 로그

### v2.0 (2025-10-27)
- 실제 구현 기반 전면 업데이트
- 7개 에이전트 시스템 반영
- 하이브리드 검색 및 4단계 검증 추가
- 실제 라이브러리 버전 명시
- 새로운 테이블 및 필드 반영

### v1.0 (2025-10-14)
- 초기 다이어그램 생성
- Docker 및 클라우드 관련 내용 제거
- 로컬 환경 중심으로 수정

---

## 📝 노트

v2 다이어그램은 2025년 10월 27일 기준으로 실제 구현된 시스템을 정확하게 반영합니다.  
향후 시스템 변경 시 다이어그램도 함께 업데이트해야 합니다.

**SVG 파일 목록**:
- 01_system_overview_v2.svg
- 02_langgraph_agents_v2.svg
- 03_pdf_processing_pipeline_v2.svg
- 04_search_answer_flow_v2.svg
- 05_database_schema_v2.svg
- 06_tech_stack_v2.svg
- 07_user_flow.svg ⭐ NEW
- viewer_v2.html

---

## 7. 사용자 플로우 (07_user_flow.svg) ⭐ NEW

### 개요
사용자 관점의 3가지 주요 시나리오를 시각화한 End-to-End 플로우입니다.

### Flow 1: AI 채팅 질의 (Chat)
1. **채팅 페이지 접속** (`/chat`)
2. **질문 입력**: "골절 시 보험금을 얼마나 받을 수 있나요?"
3. **시스템 처리** (LangGraph):
   - Router Agent: 의도 분석
   - Search Agent: 하이브리드 검색
   - Answer Agent: GPT-4o 답변 생성
4. **답변 표시 + 참조 문서**:
   - Markdown 렌더링
   - 관련 약관 [참조 1][참조 2]
   - 문서명, 페이지, 조항 번호
5. **참조 문서 클릭**: 우측 패널 열림
6. **원문 확인**: 청크 원문, 유사도 점수
7. **대화 이력 자동 저장**: chat_messages 테이블

### Flow 2: 약관 업로드 (Document Management)
1. **약관 관리 페이지** (`/documents`)
2. **업로드 버튼 클릭**: 모달 열림
3. **파일 및 정보 입력**:
   - PDF 파일 선택
   - 문서 유형 (약관/안내장)
   - 보험 종류 (건강/손해/생명)
   - 보험사명
4. **하이브리드 전처리** (백엔드):
   - Path 1: PyMuPDF4LLM
   - Path 2: GPT-4o Vision
   - Hybrid Merger
   - Quality Validator
5. **청킹 및 임베딩**:
   - TextChunker (1000 토큰)
   - EmbeddingService
   - MemoryCache 활용
6. **DB 저장**:
   - documents 테이블
   - document_chunks 테이블
   - pgvector 임베딩 저장
   - HNSW 인덱스 생성
7. **업로드 완료 알림**: 처리 결과 표시
8. **문서 목록 새로고침**: 새 약관 표시

### Flow 3: 대화 이력 관리 (Chat History)
1. **최근 대화 페이지** (`/history`)
2. **세션 목록 로드**: chat_sessions 조회 (최신순)
3. **세션 목록 표시**:
   - 세션 제목 (첫 질문)
   - 생성 시간
   - 메시지 개수
4. **세션 선택 (클릭)**: thread_id 전달
5. **메시지 로드**: chat_messages 조회 (시간순)
6. **대화 내역 표시**:
   - 사용자 질문 (파란색)
   - AI 답변 (회색)
   - 시간 스탬프
7. **의사결정**:
   - 계속 대화 → 채팅 페이지 이동 (세션 이어가기)
   - 종료 → 페이지 유지

### 공통 기능 (Cross-Cutting Features)
- **로딩 상태 표시**: 모든 비동기 작업에 스피너/프로그레스바
- **에러 핸들링**: 실패 시 사용자 친화적 메시지 (Toast/Alert)
- **자동 저장**: 대화 내역 자동 DB 저장 (백그라운드)
- **Markdown 렌더링**: react-markdown으로 답변 포맷팅

