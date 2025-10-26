# ISPL 아키텍처 다이어그램

보험 약관 기반 AI 챗봇 서비스의 시스템 아키텍처를 시각화한 다이어그램 모음입니다.

---

## 📊 다이어그램 목록

### 1. 시스템 개요 (01_system_overview.svg)
전체 시스템의 구성 요소와 데이터 흐름을 한눈에 보여줍니다.

**주요 구성 요소**:
- 사용자 인터페이스 (Next.js)
- API 서버 (FastAPI)
- LangGraph 멀티 에이전트 시스템
- PostgreSQL + pgvector
- OpenAI API 통합

---

### 2. LangGraph 멀티 에이전트 (02_langgraph_agents.svg)
LangGraph 기반 멀티 에이전트 시스템의 구조와 라우팅 로직을 상세히 설명합니다.

**에이전트 구성**:
- **Router Agent**: 사용자 의도 분석 및 작업 라우팅
- **Search Agent**: 벡터 검색 및 컨텍스트 검색
- **Answer Agent**: RAG 기반 답변 생성
- **Processing Agent**: PDF 자동 처리 파이프라인
- **Management Agent**: 약관 관리 및 CRUD 작업

**상태 관리**:
- StateGraph를 통한 상태 전파
- Command 객체로 에이전트 간 라우팅
- 메시지 히스토리 관리

---

### 3. PDF 처리 파이프라인 (03_pdf_processing_pipeline.svg)
PDF 업로드부터 벡터 임베딩까지의 하이브리드 전처리 파이프라인을 설명합니다.

**처리 단계**:
1. **PDF 업로드**: 사용자가 보험 약관 PDF 업로드
2. **Path 1 (PyMuPDF4LLM)**: 직접 텍스트 추출 → Markdown 변환
3. **Path 2 (GPT-4 Vision)**: PDF → 이미지 → AI 기반 구조 분석
4. **Merging**: 두 경로의 결과를 유사도 기반으로 병합
5. **Chunking**: 고정 크기 청크로 분할 (1000자, 100자 오버랩)
6. **Embedding**: OpenAI text-embedding-3-large (1536차원)
7. **Storage**: PostgreSQL + pgvector에 저장

---

### 4. 검색 및 답변 플로우 (04_search_answer_flow.svg)
사용자 질문부터 최종 답변까지의 전체 검색 및 생성 과정을 설명합니다.

**플로우**:
1. **사용자 질문**: 자연어 질문 입력
2. **의도 분석**: Router Agent가 질문 유형 분류
3. **쿼리 임베딩**: 질문을 벡터로 변환
4. **벡터 검색**: pgvector로 유사 청크 검색 (Top 10)
5. **컨텍스트 구성**: 검색된 청크를 컨텍스트로 조합
6. **답변 생성**: GPT-4로 RAG 답변 생성 (temp: 0.1)
7. **검증**: 소스 인용 및 할루시네이션 방지
8. **응답 반환**: 사용자에게 답변 전달

---

### 5. 데이터베이스 스키마 (05_database_schema.svg)
PostgreSQL 데이터베이스의 테이블 구조와 관계를 보여줍니다.

**주요 테이블**:
- **users**: 사용자 정보
- **documents**: 보험 약관 문서 메타데이터
- **document_chunks**: 벡터 임베딩 저장 (VECTOR(1536))
- **processing_logs**: PDF 처리 이력
- **search_logs**: 검색 쿼리 로그

**인덱스**:
- HNSW 인덱스 (m=32, ef_construction=200)
- Cosine Similarity 연산자

---

### 6. 기술 스택 (06_tech_stack.svg)
프로젝트에서 사용하는 모든 기술 스택을 카테고리별로 정리합니다.

**Frontend**:
- Next.js 15 (App Router)
- React 18
- TypeScript
- Tailwind CSS
- Shadcn/ui

**Backend**:
- FastAPI
- Python 3.11+
- Pydantic
- SQLAlchemy (ORM)
- LangGraph

**AI/ML**:
- OpenAI GPT-4
- GPT-4 Vision
- text-embedding-3-large
- LangChain
- LangGraph

**Data Processing**:
- PyMuPDF4LLM
- pdf2image
- OpenCV / Pillow
- py-hanspell
- SequenceMatcher
- tiktoken

**Database**:
- PostgreSQL 17.6
- pgvector
- HNSW 인덱스
- Cosine Similarity
- Full-Text Search
- Connection Pooling

**Infrastructure**:
- Redis (캐싱, 선택사항)
- 로컬 개발 환경

---

## 🎨 다이어그램 특징

### 색상 코드
- **파란색**: Frontend / 입력 / 사용자
- **주황색**: Backend / API
- **보라색**: AI/ML / LLM
- **녹색**: 데이터 처리
- **청록색**: 데이터베이스
- **회색**: 인프라

### 아이콘
- 📄 PDF 문서
- 🔍 검색
- 🤖 AI 에이전트
- 💾 데이터베이스
- ⚡ API

---

## 📖 사용 방법

### 1. 브라우저에서 보기
`viewer.html` 파일을 브라우저로 열면 모든 다이어그램을 한 화면에서 볼 수 있습니다.

```bash
# Windows
start doc/architecture/viewer.html

# Mac/Linux
open doc/architecture/viewer.html
```

### 2. 개별 SVG 파일 보기
각 SVG 파일을 직접 브라우저나 SVG 뷰어로 열 수 있습니다.

### 3. 문서에 포함
Markdown이나 HTML 문서에 이미지로 포함할 수 있습니다.

```markdown
![시스템 개요](./architecture/01_system_overview.svg)
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
- [연구 보고서](../ISPL_Research_Report.md)
- [작업 계획](../ISPL_Task_Plan_v2.md)

---

## ✅ 업데이트 로그

- **2025-10-14**: 초기 다이어그램 생성
- **2025-10-14**: Docker 및 클라우드 관련 내용 제거, 로컬 환경 중심으로 수정

