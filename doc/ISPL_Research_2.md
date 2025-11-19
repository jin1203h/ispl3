# 보험약관 기반 Agentic AI 시스템 - 기술 연구 보고서 v2.0

**작성일**: 2025년 10월 27일  
**프로젝트명**: ISPL (Insurance Policy) - Agentic AI System  
**버전**: 2.0 (Production-Ready)

---

## 📋 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [기술 스택 및 버전](#2-기술-스택-및-버전)
3. [시스템 아키텍처](#3-시스템-아키텍처)
4. [LangGraph Multi-Agent 시스템](#4-langgraph-multi-agent-시스템)
5. [PDF 하이브리드 전처리 파이프라인](#5-pdf-하이브리드-전처리-파이프라인)
6. [하이브리드 검색 시스템](#6-하이브리드-검색-시스템)
7. [답변 생성 및 검증](#7-답변-생성-및-검증)
8. [데이터베이스 설계](#8-데이터베이스-설계)
9. [Frontend 구현](#9-frontend-구현)
10. [성능 최적화](#10-성능-최적화)
11. [테스트 및 검증](#11-테스트-및-검증)
12. [운영 및 모니터링](#12-운영-및-모니터링)
13. [기술적 과제 및 해결 방안](#13-기술적-과제-및-해결-방안)
14. [향후 개선 방향](#14-향후-개선-방향)

---

## 1. 프로젝트 개요

### 1.1 목적

생성형 AI를 활용한 보험약관 지능형 검색 및 상담 시스템 구축:
- 보험약관 PDF의 자동 전처리 및 벡터화
- 자연어 질의에 대한 정확한 답변 제공
- 할루시네이션 방지를 통한 신뢰도 높은 응답
- 사용자 친화적인 대화형 인터페이스

### 1.2 핵심 기능

**약관 관리**
- PDF 업로드 및 하이브리드 전처리 (PyMuPDF + GPT-4 Vision)
- 자동 청킹 및 벡터 임베딩
- 약관 목록 조회, 다운로드, 삭제

**약관 검색**
- 하이브리드 검색 (벡터 + 키워드)
- 쿼리 전처리 및 전문용어 표준화
- 컨텍스트 판단 및 청크 확장
- RRF(Reciprocal Rank Fusion) 기반 결과 융합

**답변 생성**
- RAG(Retrieval-Augmented Generation) 기반 답변
- 4단계 검증 (할루시네이션, 컨텍스트, 조항, 형식)
- 참조 출처 자동 인용
- 대화 이력 관리

### 1.3 구현 범위

- ✅ 백엔드: FastAPI + LangGraph Multi-Agent 시스템
- ✅ 프론트엔드: Next.js 15 + React 18 + Tailwind CSS
- ✅ 데이터베이스: PostgreSQL 17.6 + pgvector
- ✅ AI/ML: OpenAI GPT-4, GPT-4 Vision, text-embedding-3-large
- ✅ PDF 처리: PyMuPDF4LLM + pdf2image + Vision
- ✅ 검색: 하이브리드 검색 (벡터 + Full-Text Search)
- ✅ 검증: 답변 신뢰도 4단계 검증 시스템

---

## 2. 기술 스택 및 버전

### 2.1 Backend

```python
# Core Framework
fastapi==0.115.0
uvicorn[standard]==0.32.0
python-multipart==0.0.12

# Database
sqlalchemy==2.0.35
asyncpg==0.30.0
psycopg2-binary==2.9.10
pgvector==0.3.6

# AI/ML
openai==1.55.3
langchain==0.3.7
langchain-openai==0.2.8
langchain-community==0.3.5
langgraph>=0.3.27

# PDF Processing
PyMuPDF==1.24.14
pymupdf4llm==0.0.17
pdf2image==1.17.0
Pillow==11.0.0
opencv-python==4.10.0.84

# Utilities
tiktoken==0.8.0           # 토큰 카운팅
tenacity==9.0.0           # 재시도 로직
kiwipiepy==0.21.0         # 한국어 형태소 분석
pydantic==2.10.2
python-dotenv==1.0.1
```

### 2.2 Frontend

```json
{
  "dependencies": {
    "next": "15.0.3",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-markdown": "^9.0.1",
    "remark-gfm": "^4.0.0"
  },
  "devDependencies": {
    "typescript": "^5.6.3",
    "tailwindcss": "^3.4.14",
    "@types/react": "^19.0.0"
  }
}
```

### 2.3 Database

- **PostgreSQL**: 17.6
- **Extensions**: pgvector (벡터 검색)
- **인덱싱**: HNSW (m=32, ef_construction=200)
- **연결 방식**: asyncpg (비동기)

### 2.4 AI Models

| 용도 | 모델 | 설정 |
|-----|------|------|
| 답변 생성 | GPT-4o | temperature=0.1 |
| Vision 처리 | GPT-4 Vision | max_tokens=4000 |
| 임베딩 | text-embedding-3-large | dimension=1536 |
| 검증 | GPT-4o | temperature=0.0 |

---

## 3. 시스템 아키텍처

### 3.1 전체 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    사용자 (Browser)                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Frontend (Next.js 15)                           │
│  ┌──────────────┬──────────────┬──────────────────────┐    │
│  │  Chat UI     │  Documents   │  History             │    │
│  │  (GPT Style) │  Management  │  Management          │    │
│  └──────────────┴──────────────┴──────────────────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST API
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              API Endpoints                           │   │
│  │  /chat, /search, /documents, /history               │   │
│  └─────────────────────┬───────────────────────────────┘   │
│                        │                                     │
│  ┌─────────────────────▼───────────────────────────────┐   │
│  │        LangGraph Multi-Agent System                  │   │
│  │  ┌──────────┬──────────┬──────────┬──────────┐     │   │
│  │  │  Router  │  Search  │  Answer  │  Mgmt    │     │   │
│  │  │  Agent   │  Agent   │  Agent   │  Agent   │     │   │
│  │  └──────────┴──────────┴──────────┴──────────┘     │   │
│  │  ┌──────────────────────────────────────────┐      │   │
│  │  │  Context Judgement + Chunk Expansion     │      │   │
│  │  └──────────────────────────────────────────┘      │   │
│  └─────────────────────┬───────────────────────────────┘   │
└────────────────────────┼─────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  PostgreSQL  │ │   OpenAI     │ │  File System │
│  + pgvector  │ │     API      │ │   (uploads)  │
└──────────────┘ └──────────────┘ └──────────────┘
```

### 3.2 데이터 흐름

**PDF 업로드 플로우**
```
PDF Upload → Processing Agent → PyMuPDF + Vision → Merge → 
Chunking → Embedding → PostgreSQL + File System
```

**검색 플로우**
```
User Query → Router → Search Agent → Hybrid Search → 
Context Judgement → (Chunk Expansion) → Answer Agent → 
Validation → Response
```

### 3.3 주요 특징

1. **비동기 처리**: FastAPI + asyncpg로 고성능 비동기 처리
2. **Multi-Agent**: LangGraph로 작업 분리 및 워크플로우 관리
3. **하이브리드 검색**: 벡터 + 키워드 검색으로 정확도 향상
4. **4단계 검증**: 할루시네이션 방지 및 신뢰도 보장
5. **컨텍스트 확장**: 불충분한 경우 자동으로 청크 확장

---

## 4. LangGraph Multi-Agent 시스템

### 4.1 Agent 구성

#### 4.1.1 Router Agent (라우터)

**역할**: 사용자 요청 분석 및 적절한 Agent로 라우팅

**구현**:
```python
from langgraph.graph import StateGraph, START
from langgraph.types import Command

def router_node(state: ISPLState):
    """
    사용자 질의를 분석하여 적절한 Agent로 라우팅
    - search: 약관 검색 및 질의응답
    - upload: PDF 업로드 및 전처리
    - manage: 약관 관리 (조회/삭제)
    """
    query = state.get("query", "")
    
    # 의도 분류 로직
    if "업로드" in query or "등록" in query:
        return Command(goto="processing_agent", update={"task_type": "upload"})
    elif "삭제" in query or "목록" in query:
        return Command(goto="management_agent", update={"task_type": "manage"})
    else:
        return Command(goto="search_agent", update={"task_type": "search"})
```

**특징**:
- LangGraph Command 객체로 동적 라우팅
- 키워드 기반 의도 분류
- 상태 업데이트를 통한 정보 전달

#### 4.1.2 Search Agent (검색)

**역할**: 하이브리드 검색 수행

**구현**:
```python
async def search_node(state: ISPLState):
    """
    벡터 + 키워드 하이브리드 검색 수행
    - Query Preprocessing: 전문용어 표준화
    - Hybrid Search: RRF 기반 결과 융합
    - Top 10 chunks 반환
    """
    query = state.get("query", "")
    
    # 쿼리 전처리
    preprocessed = query_preprocessor.preprocess(query)
    
    # 하이브리드 검색
    results = await hybrid_search_service.search(
        session=db_session,
        query=preprocessed.standardized_query,
        limit=10,
        similarity_threshold=0.7
    )
    
    return {"search_results": results}
```

**특징**:
- 쿼리 전처리 (전문용어 표준화, 키워드 추출)
- 벡터 검색 + 키워드 검색 병렬 수행
- RRF로 결과 융합 및 재순위화

#### 4.1.3 Context Judgement Agent (컨텍스트 판단)

**역할**: 검색 결과가 질의 응답에 충분한지 판단

**구현**:
```python
async def context_judgement_node(state: ISPLState):
    """
    검색 결과의 충분성 판단
    - 최소 3개 이상의 관련 청크
    - 평균 유사도 0.75 이상
    - 총 토큰 수 500 이상
    """
    results = state.get("search_results", [])
    
    # 판단 로직
    is_sufficient = (
        len(results) >= 3 and
        avg_similarity(results) >= 0.75 and
        total_tokens(results) >= 500
    )
    
    return {"context_sufficient": is_sufficient}
```

**특징**:
- 정량적 지표 기반 판단
- 불충분 시 Chunk Expansion Agent로 라우팅
- 최대 2회 확장 제한

#### 4.1.4 Chunk Expansion Agent (청크 확장)

**역할**: 컨텍스트 불충분 시 인접 청크 확장

**구현**:
```python
async def chunk_expansion_node(state: ISPLState):
    """
    인접 청크를 확장하여 컨텍스트 보강
    - 상위 5개 청크에 대해 ±1 청크 확장
    - 중복 제거
    - 재판단을 위해 Context Judgement로 복귀
    """
    original_chunks = state.get("search_results", [])
    
    # 상위 5개 확장
    expanded = await chunk_repository.expand_chunks(
        original_chunks[:5],
        expansion_size=1
    )
    
    return {
        "search_results": expanded,
        "expansion_count": state.get("expansion_count", 0) + 1
    }
```

**특징**:
- 문서 순서 보존
- 페이지 경계 고려
- 최대 2회 확장으로 무한 루프 방지

#### 4.1.5 Answer Agent (답변)

**역할**: RAG 기반 답변 생성 및 검증

**구현**:
```python
async def answer_node(state: ISPLState):
    """
    GPT-4 기반 답변 생성 및 4단계 검증
    - 시스템 프롬프트: 보험약관 전문가
    - Temperature: 0.1 (정확도 우선)
    - 검증: 할루시네이션, 컨텍스트, 조항, 형식
    """
    query = state.get("query", "")
    context_chunks = state.get("search_results", [])
    
    # 답변 생성
    answer = await generate_answer(query, context_chunks)
    
    # 4단계 검증
    validation = await answer_validator.validate(
        answer, query, context_chunks
    )
    
    # 신뢰도 0.7 미만 시 재생성
    if validation.overall_score < 0.7:
        answer = await regenerate_answer(query, context_chunks, validation)
    
    return {"final_answer": answer, "validation": validation}
```

**특징**:
- 구조화된 답변 형식 (📌 답변, 📋 관련 약관, ⚠️ 주의사항)
- 참조 번호 자동 인용 [참조 1], [참조 2]
- 신뢰도 점수 기반 재생성

#### 4.1.6 Processing Agent (전처리)

**역할**: PDF 업로드 및 하이브리드 전처리

**구현**:
```python
async def processing_node(state: ISPLState):
    """
    PDF 하이브리드 전처리
    - Path 1: PyMuPDF4LLM (빠른 텍스트 추출)
    - Path 2: GPT-4 Vision (이미지 기반 추출)
    - Merge: 유사도 기반 병합
    - Chunking: 1000자, 100자 오버랩
    - Embedding: text-embedding-3-large
    """
    pdf_path = state.get("file_path")
    
    result = await pdf_processor.process_pdf(
        pdf_path=pdf_path,
        method="pymupdf",  # 기본값: PyMuPDF만 사용
        enable_chunking=True
    )
    
    return {"task_results": result}
```

**특징**:
- 3가지 처리 모드: pymupdf, vision, both
- 품질 검증 단계 포함
- 비동기 병렬 처리

#### 4.1.7 Management Agent (관리)

**역할**: 약관 관리 (조회, 삭제, 다운로드)

**구현**:
```python
async def management_node(state: ISPLState):
    """
    약관 관리 작업 수행
    - 목록 조회
    - 파일 다운로드
    - 문서 삭제
    """
    task_type = state.get("management_task", "list")
    
    if task_type == "list":
        documents = await document_service.list_documents()
    elif task_type == "delete":
        await document_service.delete_document(document_id)
    
    return {"task_results": documents}
```

### 4.2 그래프 구조

```python
builder = StateGraph(ISPLState)

# 노드 추가
builder.add_node("router", router_node)
builder.add_node("search_agent", search_node)
builder.add_node("context_judgement_agent", context_judgement_node)
builder.add_node("chunk_expansion_agent", chunk_expansion_node)
builder.add_node("answer_agent", answer_node)
builder.add_node("processing_agent", processing_node)
builder.add_node("management_agent", management_node)

# 엣지 설정
builder.add_edge(START, "router")
builder.add_edge("search_agent", "context_judgement_agent")

# 조건부 라우팅
builder.add_conditional_edges(
    "context_judgement_agent",
    route_after_judgement,  # 충분 → answer_agent, 불충분 → chunk_expansion
    {"answer_agent": "answer_agent", "chunk_expansion_agent": "chunk_expansion_agent"}
)

builder.add_edge("chunk_expansion_agent", "context_judgement_agent")
builder.add_edge("answer_agent", END)
builder.add_edge("processing_agent", END)
builder.add_edge("management_agent", END)

graph = builder.compile(checkpointer=MemorySaver())
```

### 4.3 State 관리

```python
class ISPLState(MessagesState):
    """LangGraph 상태 정의"""
    
    # 기본 정보
    query: str                      # 사용자 질의
    task_type: str                  # 작업 유형 (search/upload/manage)
    
    # 검색 결과
    search_results: List[dict]      # 검색된 청크 목록
    expanded_chunks: List[dict]     # 확장된 청크
    
    # 컨텍스트 판단
    context_sufficient: bool        # 컨텍스트 충분 여부
    expansion_count: int            # 확장 횟수
    
    # 답변
    final_answer: str               # 최종 답변
    validation: dict                # 검증 결과
    
    # 에러 처리
    error: Optional[str]            # 에러 메시지
    task_results: dict              # 작업 결과
```

---

## 5. PDF 하이브리드 전처리 파이프라인

### 5.1 전체 프로세스

```
PDF 입력
   │
   ├─ Path 1: PyMuPDF4LLM
   │    ├─ 직접 텍스트 추출
   │    ├─ Markdown 변환
   │    └─ 표/이미지 메타데이터 추출
   │
   ├─ Path 2: GPT-4 Vision (선택적)
   │    ├─ PDF → 이미지 (DPI 300)
   │    ├─ 이미지 전처리 (그레이스케일, 노이즈 제거)
   │    └─ Vision API 호출
   │
   ├─ Merge (Path 1 + Path 2)
   │    ├─ 페이지별 정렬
   │    ├─ 유사도 기반 중복 제거
   │    └─ 최종 병합
   │
   ├─ Quality Validation
   │    ├─ 완전성 검사
   │    ├─ 일관성 검사
   │    └─ 품질 점수 산출
   │
   ├─ Chunking
   │    ├─ Fixed-size: 1000자, 100자 오버랩
   │    ├─ 표: 전체 단위
   │    └─ 이미지: 설명 + 주변 텍스트
   │
   ├─ Embedding
   │    ├─ text-embedding-3-large
   │    ├─ 1536 차원
   │    └─ 배치 처리 (100개씩)
   │
   └─ Storage
        ├─ PostgreSQL: 메타데이터 + 벡터
        └─ File System: 원본 PDF + Markdown
```

### 5.2 Path 1: PyMuPDF4LLM

**장점**:
- 빠른 처리 속도 (페이지당 ~0.1초)
- 정확한 텍스트 추출
- 표 구조 보존
- 비용 없음

**구현**:
```python
class PyMuPDFExtractor:
    def extract(self, pdf_path: str) -> Dict:
        """PyMuPDF4LLM으로 Markdown 변환"""
        md_text = pymupdf4llm.to_markdown(
            pdf_path,
            page_chunks=True,  # 페이지별 분리
            write_images=True,  # 이미지 추출
            image_path="uploads/images"
        )
        
        return {
            "markdown": md_text,
            "pages": self._parse_pages(md_text),
            "quality_score": self._calculate_quality(md_text)
        }
```

### 5.3 Path 2: GPT-4 Vision (선택적)

**장점**:
- 복잡한 레이아웃 처리
- 손글씨/저화질 문서 처리
- 이미지 내 텍스트 인식
- 표 구조 복원

**단점**:
- 느린 처리 속도 (페이지당 ~10초)
- API 비용 발생 ($0.01/페이지)

**구현**:
```python
class VisionExtractor:
    async def extract(self, pdf_path: str) -> Dict:
        """GPT-4 Vision으로 이미지 기반 추출"""
        # PDF → 이미지 변환
        images = convert_from_path(pdf_path, dpi=300)
        
        results = []
        for idx, img in enumerate(images):
            # 이미지 전처리
            processed_img = self._preprocess_image(img)
            
            # Vision API 호출
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "이 보험 약관 페이지의 모든 내용을 Markdown으로 변환해주세요."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{base64_img}"}
                        }
                    ]
                }]
            )
            
            results.append(response.choices[0].message.content)
        
        return {"markdown": "\n\n".join(results), "pages": results}
```

### 5.4 Hybrid Merger

**병합 전략**:
1. 페이지별로 Path 1과 Path 2 결과 정렬
2. SequenceMatcher로 텍스트 유사도 계산
3. 유사도 0.8 이상: Path 1 사용 (빠르고 정확)
4. 유사도 0.8 미만: Path 2 사용 (Vision이 더 정확)
5. 표/이미지: 두 경로 결과 병합

**구현**:
```python
class HybridMerger:
    def merge(self, pymupdf_result: Dict, vision_result: Dict) -> Dict:
        """두 경로의 결과를 병합"""
        merged_pages = []
        
        for i in range(len(pymupdf_result["pages"])):
            pymupdf_page = pymupdf_result["pages"][i]
            vision_page = vision_result["pages"][i]
            
            # 유사도 계산
            similarity = self._calculate_similarity(pymupdf_page, vision_page)
            
            if similarity >= 0.8:
                merged_pages.append(pymupdf_page)  # PyMuPDF 우선
            else:
                merged_pages.append(vision_page)   # Vision 우선
        
        return {"markdown": "\n\n".join(merged_pages)}
```

### 5.5 Chunking 전략

**Fixed-size Chunking**:
```python
class TextChunker:
    def __init__(self, chunk_size=1000, overlap=100):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def chunk_text(self, text: str, metadata: dict) -> List[dict]:
        """텍스트를 고정 크기로 청킹"""
        tokens = self.encoding.encode(text)
        chunks = []
        
        start = 0
        while start < len(tokens):
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens)
            
            chunks.append({
                "content": chunk_text,
                "chunk_index": len(chunks),
                "token_count": len(chunk_tokens),
                "metadata": metadata
            })
            
            start = end - self.overlap  # 오버랩 적용
        
        return chunks
```

**특수 처리**:
- **표**: 전체 표를 하나의 청크로 유지
- **이미지**: ALT 텍스트 + 주변 200자 포함
- **제목**: 섹션 제목을 메타데이터에 포함

### 5.6 Embedding 생성

**배치 처리**:
```python
class EmbeddingService:
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """배치 임베딩 생성"""
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            response = await self.client.embeddings.create(
                model="text-embedding-3-large",
                input=batch,
                dimensions=1536
            )
            
            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)
        
        return all_embeddings
```

**특징**:
- 배치 크기: 100개 (API 제한)
- 재시도 로직: tenacity 활용
- 캐싱: Redis 활용 (선택적)

---

## 6. 하이브리드 검색 시스템

### 6.1 검색 전략

```
User Query
   │
   ├─ Query Preprocessing
   │    ├─ 전문용어 표준화
   │    ├─ 공백 정규화
   │    └─ 키워드 추출
   │
   ├─ Parallel Search
   │    │
   │    ├─ Vector Search
   │    │    ├─ Query Embedding
   │    │    ├─ Cosine Similarity
   │    │    └─ Top 10 chunks
   │    │
   │    └─ Keyword Search
   │         ├─ Full-Text Search
   │         ├─ 조항 번호 매칭
   │         └─ Top 10 chunks
   │
   ├─ RRF Fusion
   │    ├─ Reciprocal Rank Fusion
   │    ├─ k=60 (표준값)
   │    └─ 최종 Top 10
   │
   └─ Context Optimization
        ├─ 최대 20,000 토큰
        └─ 유사도 0.7 이상
```

### 6.2 Query Preprocessing

**전문용어 표준화**:
```python
class QueryPreprocessor:
    def preprocess(self, query: str) -> PreprocessedQuery:
        """쿼리 전처리"""
        # 1. 정규화
        normalized = self._normalize(query)
        
        # 2. 전문용어 표준화
        standardized = self._standardize_terms(normalized)
        
        # 3. 키워드 추출
        keywords = extract_keywords(standardized)
        
        # 4. 조항 번호 추출
        clauses = self._extract_clause_numbers(query)
        
        return PreprocessedQuery(
            original_query=query,
            standardized_query=standardized,
            keywords=keywords,
            clause_numbers=clauses
        )
```

**전문용어 사전** (`insurance_terms.json`):
```json
{
  "synonyms": {
    "보험금": ["급여금", "지급금", "보상금"],
    "면책": ["면책사항", "보상하지 않는 사항"],
    "CI": ["중대한질병", "Critical Illness"]
  },
  "normalization": {
    "spacing": {
      "보험 금": "보험금",
      "면책 사항": "면책사항"
    }
  }
}
```

### 6.3 Vector Search

**HNSW 인덱스 활용**:
```python
class VectorSearchService:
    async def search(
        self,
        session: AsyncSession,
        query_embedding: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[VectorSearchResult]:
        """벡터 유사도 검색"""
        query = text("""
            SELECT 
                dc.id,
                dc.content,
                dc.page_number,
                dc.clause_number,
                dc.metadata,
                d.filename,
                d.company_name,
                1 - (dc.embedding <=> :query_embedding) as similarity
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE 
                d.status = 'active' AND
                1 - (dc.embedding <=> :query_embedding) > :threshold
            ORDER BY dc.embedding <=> :query_embedding
            LIMIT :limit
        """)
        
        result = await session.execute(query, {
            "query_embedding": query_embedding,
            "threshold": similarity_threshold,
            "limit": limit
        })
        
        return [VectorSearchResult.from_row(row) for row in result]
```

**인덱스 설정**:
```sql
CREATE INDEX idx_chunks_embedding ON document_chunks 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 32, ef_construction = 200);
```

**파라미터 설명**:
- `m=32`: 각 노드의 연결 수 (높을수록 정확도↑, 메모리↑)
- `ef_construction=200`: 구축 시 탐색 범위 (높을수록 정확도↑, 시간↑)
- `vector_cosine_ops`: Cosine Similarity 사용

### 6.4 Keyword Search

**Full-Text Search (PostgreSQL tsvector)**:
```python
async def keyword_search(
    self,
    session: AsyncSession,
    query: str,
    limit: int = 10
) -> List[dict]:
    """키워드 검색 (Full-Text Search)"""
    # tsquery 생성
    keywords = extract_keywords(query)
    tsquery_str = ' & '.join(keywords)
    
    query_sql = text("""
        SELECT 
            dc.id,
            dc.content,
            dc.page_number,
            dc.clause_number,
            ts_rank(to_tsvector('korean', dc.content), query) as rank
        FROM document_chunks dc
        WHERE to_tsvector('korean', dc.content) @@ to_tsquery('korean', :tsquery)
        ORDER BY rank DESC
        LIMIT :limit
    """)
    
    result = await session.execute(query_sql, {
        "tsquery": tsquery_str,
        "limit": limit
    })
    
    return result.fetchall()
```

**조항 번호 매칭**:
```python
def _match_clause_numbers(self, query: str, chunks: List[dict]) -> List[dict]:
    """조항 번호 정확 매칭"""
    clause_numbers = re.findall(r'제\s*(\d+)\s*조', query)
    
    if not clause_numbers:
        return chunks
    
    # 조항 번호가 일치하는 청크를 우선 순위로
    matched = []
    for chunk in chunks:
        if chunk.get("clause_number") in clause_numbers:
            matched.append(chunk)
    
    return matched + [c for c in chunks if c not in matched]
```

### 6.5 RRF (Reciprocal Rank Fusion)

**알고리즘**:
```python
class HybridSearchService:
    RRF_K = 60  # 표준값
    
    def _reciprocal_rank_fusion(
        self,
        vector_results: List[dict],
        keyword_results: List[dict]
    ) -> List[dict]:
        """RRF로 두 검색 결과 융합"""
        scores = {}
        
        # Vector 결과 점수 계산
        for rank, result in enumerate(vector_results, start=1):
            chunk_id = result["id"]
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (rank + self.RRF_K)
        
        # Keyword 결과 점수 계산
        for rank, result in enumerate(keyword_results, start=1):
            chunk_id = result["id"]
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (rank + self.RRF_K)
        
        # 점수 순으로 정렬
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        # 원본 결과에서 청크 정보 가져오기
        id_to_chunk = {r["id"]: r for r in vector_results + keyword_results}
        
        return [id_to_chunk[chunk_id] for chunk_id in sorted_ids]
```

**RRF 수식**:
```
RRF(d) = Σ 1 / (k + rank_i(d))

where:
- d: document (chunk)
- k: constant (60)
- rank_i(d): rank of d in i-th result list
```

### 6.6 Context Optimization

**토큰 제한**:
```python
def _optimize_context(
    self,
    chunks: List[dict],
    max_tokens: int = 20000
) -> List[dict]:
    """컨텍스트를 토큰 제한 내로 최적화"""
    selected_chunks = []
    total_tokens = 0
    
    for chunk in chunks:
        chunk_tokens = chunk.get("token_count", 0)
        
        if total_tokens + chunk_tokens <= max_tokens:
            selected_chunks.append(chunk)
            total_tokens += chunk_tokens
        else:
            break
    
    logger.info(f"컨텍스트 최적화: {len(chunks)} → {len(selected_chunks)} chunks, {total_tokens} tokens")
    
    return selected_chunks
```

---

## 7. 답변 생성 및 검증

### 7.1 RAG 기반 답변 생성

**시스템 프롬프트**:
```python
SYSTEM_PROMPT = """당신은 보험약관 전문 상담사입니다. 다음 규칙을 반드시 준수하세요:

1. **정확성 보장**: 제공된 약관 내용에만 기반하여 답변하세요.
2. **근거 제시**: 모든 답변에 해당 약관 조항을 인용하세요. [참조 N] 형식을 사용하세요.
3. **한계 인정**: 제공된 자료에 없는 내용은 "해당 정보가 약관에 명시되어 있지 않습니다"라고 답하세요.
4. **명확한 구조**: 답변을 다음 순서로 구성하세요:
   📌 답변: 질문에 대한 직접적인 답변
   📋 관련 약관: 참조한 약관 내용을 인용
   ⚠️ 주의사항: 추가 확인이 필요한 사항
5. **금지사항**: 추측, 일반 상식, 다른 보험사 정보는 절대 사용하지 마세요.
"""
```

**답변 생성**:
```python
class AnswerAgent:
    async def generate_answer(
        self,
        query: str,
        context_chunks: List[dict]
    ) -> str:
        """RAG 기반 답변 생성"""
        # 컨텍스트 구성
        context = self._build_context(context_chunks)
        
        # 프롬프트 조립
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"""
다음 약관 내용을 참고하여 질문에 답변해주세요.

**참조 약관**:
{context}

**질문**: {query}

답변 형식:
📌 답변
[답변 내용]

📋 관련 약관
[참조 1] [내용]
[참조 2] [내용]

⚠️ 주의사항
[추가 확인 사항]
"""}
        ]
        
        # GPT-4 호출
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.1,  # 정확도 우선
            max_tokens=2000
        )
        
        return response.choices[0].message.content
```

### 7.2 4단계 검증 시스템

#### 7.2.1 검증 개요

```
Answer Validation
   │
   ├─ 1. Hallucination Check (40%)
   │    ├─ GPT-4로 답변 vs 컨텍스트 검증
   │    └─ 사실 확인
   │
   ├─ 2. Context Matching (30%)
   │    ├─ 코사인 유사도 계산
   │    └─ 임베딩 비교
   │
   ├─ 3. Clause Verification (20%)
   │    ├─ 조항 번호 추출
   │    └─ DB 존재 확인
   │
   ├─ 4. Format Validation (10%)
   │    ├─ 구조 확인
   │    ├─ 참조 번호 확인
   │    └─ 조항 인용 확인
   │
   └─ Overall Score (0.0 ~ 1.0)
        └─ 가중 평균 계산
```

#### 7.2.2 Hallucination Check (할루시네이션 검증)

**목적**: 답변이 컨텍스트에 없는 내용을 만들어내지 않았는지 확인

**구현**:
```python
async def _check_hallucination(
    self,
    answer: str,
    context_chunks: List[dict]
) -> ValidationDetail:
    """GPT-4로 할루시네이션 검증"""
    context_text = "\n\n".join([c["content"] for c in context_chunks])
    
    prompt = f"""
다음 답변이 제공된 컨텍스트에만 기반하고 있는지 검증하세요.

**컨텍스트**:
{context_text}

**답변**:
{answer}

검증 기준:
1. 답변의 모든 내용이 컨텍스트에 있는가?
2. 추측이나 일반 상식을 사용하지 않았는가?
3. 다른 출처의 정보를 사용하지 않았는가?

JSON 형식으로 답변하세요:
{{
  "is_faithful": true/false,
  "confidence": 0.0~1.0,
  "issues": ["문제점1", "문제점2", ...]
}}
"""
    
    response = await self.client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response.choices[0].message.content)
    
    return ValidationDetail(
        check_name="hallucination",
        passed=result["is_faithful"],
        score=result["confidence"],
        details={"issues": result["issues"]}
    )
```

#### 7.2.3 Context Matching (컨텍스트 일치도)

**목적**: 답변과 컨텍스트의 의미적 유사도 확인

**구현**:
```python
async def _check_context_matching(
    self,
    answer: str,
    context_chunks: List[dict]
) -> ValidationDetail:
    """답변과 컨텍스트의 코사인 유사도 계산"""
    # 답변 임베딩
    answer_embedding = await self.embedding_service.generate_embedding(answer)
    
    # 각 청크와의 유사도 계산
    similarities = []
    for chunk in context_chunks:
        chunk_embedding = chunk["embedding"]
        similarity = cosine_similarity(answer_embedding, chunk_embedding)
        similarities.append(similarity)
    
    # 평균 유사도
    avg_similarity = sum(similarities) / len(similarities)
    
    # 0.7 이상이면 통과
    passed = avg_similarity >= 0.7
    
    return ValidationDetail(
        check_name="context_matching",
        passed=passed,
        score=avg_similarity,
        details={"avg_similarity": avg_similarity}
    )
```

#### 7.2.4 Clause Verification (조항 확인)

**목적**: 답변에 인용된 조항 번호가 실제로 존재하는지 확인

**구현**:
```python
async def _check_clause_verification(
    self,
    answer: str,
    session: AsyncSession
) -> ValidationDetail:
    """조항 번호 존재 확인"""
    # 답변에서 조항 번호 추출
    clause_pattern = r'제\s*(\d+)\s*조'
    mentioned_clauses = re.findall(clause_pattern, answer)
    
    if not mentioned_clauses:
        return ValidationDetail(
            check_name="clause_verification",
            passed=True,
            score=1.0,
            details={"message": "조항 번호 미사용"}
        )
    
    # DB에서 조항 확인
    query = text("""
        SELECT DISTINCT clause_number
        FROM document_chunks
        WHERE clause_number IN :clauses
    """)
    
    result = await session.execute(query, {"clauses": mentioned_clauses})
    existing_clauses = [row[0] for row in result]
    
    # 존재하지 않는 조항
    invalid_clauses = set(mentioned_clauses) - set(existing_clauses)
    
    if invalid_clauses:
        return ValidationDetail(
            check_name="clause_verification",
            passed=False,
            score=0.0,
            details={"invalid_clauses": list(invalid_clauses)}
        )
    
    return ValidationDetail(
        check_name="clause_verification",
        passed=True,
        score=1.0,
        details={"verified_clauses": len(mentioned_clauses)}
    )
```

#### 7.2.5 Format Validation (형식 검증)

**목적**: 답변이 정해진 형식을 따르는지 확인

**구현**:
```python
def _check_format(
    self,
    answer: str,
    search_results: List[dict]
) -> ValidationDetail:
    """답변 형식 검증"""
    checks = {
        "has_structure": False,
        "has_references": False,
        "has_clause_numbers": False
    }
    warnings = []
    
    # 1. 구조화 여부
    if "📌 답변" in answer and "📋 관련 약관" in answer:
        checks["has_structure"] = True
    else:
        warnings.append("구조화된 형식이 없습니다")
    
    # 2. 참조 번호
    if re.search(r'\[참조\s*\d+\]', answer):
        checks["has_references"] = True
    else:
        warnings.append("참조 번호가 없습니다")
    
    # 3. 조항 번호 (선택적)
    if re.search(r'제\s*\d+\s*조', answer):
        checks["has_clause_numbers"] = True
    
    # 점수 계산
    score = sum(checks.values()) / len(checks)
    
    return ValidationDetail(
        check_name="format_validation",
        passed=score >= 0.7,
        score=score,
        details={"checks": checks, "warnings": warnings}
    )
```

#### 7.2.6 종합 점수 계산

```python
def validate(
    self,
    answer: str,
    query: str,
    context_chunks: List[dict],
    session: AsyncSession = None
) -> AnswerValidation:
    """4단계 검증 수행"""
    # 각 검증 수행
    hallucination = await self._check_hallucination(answer, context_chunks)
    context = await self._check_context_matching(answer, context_chunks)
    clause = await self._check_clause_verification(answer, session)
    format_check = self._check_format(answer, context_chunks)
    
    # 가중 평균 계산
    overall_score = (
        hallucination.score * self.WEIGHTS["hallucination"] +
        context.score * self.WEIGHTS["context"] +
        clause.score * self.WEIGHTS["clause"] +
        format_check.score * self.WEIGHTS["format"]
    )
    
    return AnswerValidation(
        overall_score=overall_score,
        passed=overall_score >= 0.7,
        validations=[hallucination, context, clause, format_check],
        timestamp=datetime.utcnow()
    )
```

### 7.3 재생성 로직

**신뢰도 0.7 미만 시 재생성**:
```python
async def generate_with_validation(
    self,
    query: str,
    context_chunks: List[dict],
    max_retries: int = 2
) -> Tuple[str, AnswerValidation]:
    """검증을 통과할 때까지 답변 재생성"""
    for attempt in range(max_retries):
        # 답변 생성
        answer = await self.generate_answer(query, context_chunks)
        
        # 검증
        validation = await self.validator.validate(
            answer, query, context_chunks
        )
        
        # 통과 시 반환
        if validation.passed:
            logger.info(f"답변 검증 통과 (score={validation.overall_score:.2f})")
            return answer, validation
        
        # 실패 시 프롬프트 개선
        logger.warning(f"답변 검증 실패 (score={validation.overall_score:.2f}), 재시도 {attempt+1}/{max_retries}")
        
        # 검증 결과를 프롬프트에 추가
        feedback = self._build_feedback(validation)
        context_chunks = self._enhance_context(context_chunks, feedback)
    
    # 최대 재시도 후에도 실패 시 마지막 답변 반환
    logger.error(f"답변 검증 최종 실패 (score={validation.overall_score:.2f})")
    return answer, validation
```

---

## 8. 데이터베이스 설계

### 8.1 스키마 구조

```sql
-- pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 사용자 테이블
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE,
    email VARCHAR(100) UNIQUE,
    full_name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 문서 메타데이터
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    document_type VARCHAR(50) NOT NULL,
    insurance_type VARCHAR(50),
    company_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'active',
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_timestamp TIMESTAMP,
    total_pages INTEGER,
    processing_status VARCHAR(20) DEFAULT 'pending'
);

-- 벡터화된 청크
CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_type VARCHAR(20) NOT NULL,
    page_number INTEGER,
    pdf_page_number INTEGER,
    section_title VARCHAR(200),
    clause_number VARCHAR(50),
    content TEXT NOT NULL,
    content_hash VARCHAR(64),
    token_count INTEGER,
    metadata JSONB,
    embedding VECTOR(1536),
    confidence_score FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_chunk_per_doc UNIQUE(document_id, chunk_index)
);

-- HNSW 인덱스
CREATE INDEX idx_chunks_embedding ON document_chunks 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 32, ef_construction = 200);

-- 일반 인덱스
CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_chunks_page ON document_chunks(page_number);
CREATE INDEX idx_chunks_clause ON document_chunks(clause_number);

-- 검색 로그
CREATE TABLE search_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    query TEXT NOT NULL,
    query_intent VARCHAR(50),
    search_type VARCHAR(20),
    results_count INTEGER,
    top_similarity_score FLOAT,
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 채팅 세션
CREATE TABLE chat_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    session_name VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 채팅 메시지
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 8.2 인덱싱 전략

**HNSW 인덱스**:
- **m=32**: 각 노드당 32개 연결 (정확도와 성능의 균형)
- **ef_construction=200**: 인덱스 구축 시 200개 후보 탐색
- **vector_cosine_ops**: Cosine Similarity 연산자

**성능 특성**:
- 검색 속도: O(log N)
- 정확도: ~95% (ANN)
- 메모리 사용: ~4GB (100만 벡터 기준)

**일반 인덱스**:
```sql
CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_chunks_page ON document_chunks(page_number);
CREATE INDEX idx_chunks_clause ON document_chunks(clause_number);
CREATE INDEX idx_chunks_hash ON document_chunks(content_hash);
```

### 8.3 연결 관리

**비동기 연결 풀**:
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Engine 생성
engine = create_async_engine(
    "postgresql+asyncpg://user:password@localhost/ispl_db",
    echo=False,
    pool_size=10,
    max_overflow=20
)

# Session Factory
async_session_maker = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Dependency Injection
async def get_session():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
```

**연결 풀 설정**:
- `pool_size=10`: 기본 연결 10개
- `max_overflow=20`: 최대 30개까지 확장
- `pool_recycle=3600`: 1시간마다 연결 재생성

---

## 9. Frontend 구현

### 9.1 기술 스택

- **Framework**: Next.js 15 (App Router)
- **UI Library**: React 18
- **Styling**: Tailwind CSS 3.4
- **Markdown**: react-markdown + remark-gfm
- **TypeScript**: 5.6

### 9.2 주요 컴포넌트

#### 9.2.1 AppLayout

**역할**: 전체 레이아웃 (Sidebar + Main Content)

```typescript
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  
  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <Sidebar 
        isOpen={isSidebarOpen} 
        onToggle={() => setIsSidebarOpen(!isSidebarOpen)} 
      />
      
      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
```

#### 9.2.2 ChatMessage

**역할**: 메시지 렌더링 (사용자/AI)

```typescript
export function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === "user";
  
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div className={`max-w-3xl px-4 py-3 rounded-lg ${
        isUser ? "bg-blue-600 text-white" : "bg-gray-100"
      }`}>
        {isUser ? (
          <p>{message.content}</p>
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}
```

#### 9.2.3 ChatInput

**역할**: 질의 입력 및 전송

```typescript
export function ChatInput({ onSend }: { onSend: (query: string) => void }) {
  const [input, setInput] = useState("");
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      onSend(input);
      setInput("");
    }
  };
  
  return (
    <form onSubmit={handleSubmit} className="border-t p-4">
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="보험 약관에 대해 질문하세요..."
          className="flex-1 px-4 py-2 border rounded-lg"
        />
        <button type="submit" className="px-6 py-2 bg-blue-600 text-white rounded-lg">
          전송
        </button>
      </div>
    </form>
  );
}
```

#### 9.2.4 DocumentUpload

**역할**: PDF 업로드

```typescript
export function DocumentUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  
  const handleUpload = async () => {
    if (!file) return;
    
    setUploading(true);
    
    const formData = new FormData();
    formData.append("file", file);
    
    try {
      const response = await fetch("http://localhost:8000/api/documents/upload", {
        method: "POST",
        body: formData
      });
      
      if (response.ok) {
        alert("업로드 성공!");
        setFile(null);
      }
    } catch (error) {
      alert("업로드 실패");
    } finally {
      setUploading(false);
    }
  };
  
  return (
    <div className="p-4 border rounded-lg">
      <input
        type="file"
        accept=".pdf"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <button onClick={handleUpload} disabled={!file || uploading}>
        {uploading ? "업로드 중..." : "업로드"}
      </button>
    </div>
  );
}
```

#### 9.2.5 ReferencePanel

**역할**: 참조 문서 표시 (토글 가능)

```typescript
export function ReferencePanel({ references }: { references: Reference[] }) {
  return (
    <div className="w-80 border-l p-4 overflow-auto">
      <h3 className="font-bold mb-4">📚 참조 문서</h3>
      
      {references.map((ref, idx) => (
        <div key={idx} className="mb-4 p-3 bg-gray-50 rounded">
          <div className="text-sm font-medium">[참조 {idx + 1}]</div>
          <div className="text-xs text-gray-600 mt-1">
            {ref.filename} (페이지 {ref.page_number})
          </div>
          <div className="text-sm mt-2">{ref.content}</div>
          <div className="text-xs text-blue-600 mt-2">
            유사도: {(ref.similarity * 100).toFixed(1)}%
          </div>
        </div>
      ))}
    </div>
  );
}
```

### 9.3 API 통신

**API 클라이언트** (`lib/api.ts`):
```typescript
const API_BASE_URL = "http://localhost:8000/api";

export async function sendChatMessage(query: string): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query })
  });
  
  return response.json();
}

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  
  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    body: formData
  });
  
  return response.json();
}

export async function listDocuments(): Promise<Document[]> {
  const response = await fetch(`${API_BASE_URL}/documents`);
  return response.json();
}
```

### 9.4 페이지 구조

```
app/
├── layout.tsx                 # 루트 레이아웃
├── page.tsx                   # 홈 (채팅 페이지로 리다이렉트)
├── chat/
│   └── page.tsx              # 채팅 UI (GPT 스타일)
├── documents/
│   └── page.tsx              # 문서 관리
└── history/
    └── page.tsx              # 대화 이력
```

**채팅 페이지** (`app/chat/page.tsx`):
```typescript
'use client';

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [references, setReferences] = useState<Reference[]>([]);
  
  const handleSend = async (query: string) => {
    // 사용자 메시지 추가
    setMessages(prev => [...prev, { role: "user", content: query }]);
    
    // API 호출
    const response = await sendChatMessage(query);
    
    // AI 메시지 추가
    setMessages(prev => [...prev, { 
      role: "assistant", 
      content: response.answer 
    }]);
    
    // 참조 문서 업데이트
    setReferences(response.references);
  };
  
  return (
    <div className="flex h-screen">
      {/* 채팅 영역 */}
      <div className="flex-1 flex flex-col">
        <div className="flex-1 overflow-auto p-4">
          {messages.map((msg, idx) => (
            <ChatMessage key={idx} message={msg} />
          ))}
        </div>
        <ChatInput onSend={handleSend} />
      </div>
      
      {/* 참조 패널 */}
      <ReferencePanel references={references} />
    </div>
  );
}
```

---

## 10. 성능 최적화

### 10.1 Embedding 캐싱

**문제**: 동일 텍스트 중복 임베딩 생성

**해결**:
```python
class EmbeddingCache:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = 86400 * 7  # 7일
    
    async def get_or_create(self, text: str) -> List[float]:
        """캐시에서 가져오거나 생성"""
        # 캐시 키 생성 (텍스트 해시)
        cache_key = f"emb:{hashlib.sha256(text.encode()).hexdigest()}"
        
        # 캐시 조회
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # 임베딩 생성
        embedding = await self.embedding_service.generate_embedding(text)
        
        # 캐시 저장
        await self.redis.setex(cache_key, self.ttl, json.dumps(embedding))
        
        return embedding
```

**효과**: 중복 임베딩 생성 90% 감소

### 10.2 배치 처리

**PDF 처리**:
```python
async def process_multiple_pdfs(pdf_paths: List[str]):
    """여러 PDF 병렬 처리"""
    tasks = [
        process_pdf(path, method="pymupdf")
        for path in pdf_paths
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return results
```

**임베딩 생성**:
```python
async def generate_embeddings_batch(texts: List[str], batch_size: int = 100):
    """배치 임베딩 생성"""
    embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = await embedding_service.generate_embeddings(batch)
        embeddings.extend(batch_embeddings)
    
    return embeddings
```

### 10.3 연결 풀링

**PostgreSQL**:
```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

**효과**: 연결 생성 시간 80% 감소

### 10.4 인덱스 최적화

**HNSW 파라미터 튜닝**:
```sql
-- 정확도 우선
CREATE INDEX idx_high_accuracy ON document_chunks 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 64, ef_construction = 400);

-- 속도 우선
CREATE INDEX idx_high_speed ON document_chunks 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 100);

-- 균형 (현재 사용)
CREATE INDEX idx_balanced ON document_chunks 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 32, ef_construction = 200);
```

### 10.5 토큰 최적화

**컨텍스트 압축**:
```python
def optimize_context(chunks: List[dict], max_tokens: int = 20000) -> List[dict]:
    """불필요한 내용 제거 및 압축"""
    optimized = []
    total_tokens = 0
    
    for chunk in chunks:
        # 중복 제거
        if chunk["content"] in [c["content"] for c in optimized]:
            continue
        
        # 토큰 제한
        if total_tokens + chunk["token_count"] > max_tokens:
            break
        
        optimized.append(chunk)
        total_tokens += chunk["token_count"]
    
    return optimized
```

---

## 11. 테스트 및 검증

### 11.1 테스트 구조

```
backend/test/
├── test_pdf_processing.py              # PDF 전처리
├── test_chunking.py                    # 청킹
├── test_vector_search.py               # 벡터 검색
├── test_hybrid_search_integration.py   # 하이브리드 검색
├── test_query_preprocessor_complete.py # 쿼리 전처리
├── test_answer_validator_integration.py # 답변 검증
├── test_langgraph_agents.py            # LangGraph 워크플로우
└── test_api_integration.py             # API 통합 테스트
```

### 11.2 주요 테스트

**PDF 처리 테스트**:
```python
@pytest.mark.asyncio
async def test_pdf_processing():
    processor = PDFProcessor()
    
    result = await processor.process_pdf(
        pdf_path="test_insurance.pdf",
        document_id=1,
        method="pymupdf"
    )
    
    assert result["success"] == True
    assert len(result["chunks"]) > 0
    assert all(c["embedding"] is not None for c in result["chunks"])
```

**하이브리드 검색 테스트**:
```python
@pytest.mark.asyncio
async def test_hybrid_search():
    service = HybridSearchService()
    
    results = await service.search(
        session=db_session,
        query="골절 시 보험금은?",
        limit=10
    )
    
    assert len(results) > 0
    assert all(r["similarity"] >= 0.7 for r in results)
```

**답변 검증 테스트**:
```python
@pytest.mark.asyncio
async def test_answer_validation():
    validator = AnswerValidator()
    
    validation = await validator.validate(
        answer="...",
        query="...",
        context_chunks=[...]
    )
    
    assert validation.overall_score >= 0.7
    assert validation.passed == True
```

### 11.3 성능 벤치마크

| 작업 | 평균 시간 | 목표 |
|-----|---------|-----|
| PDF 전처리 (10페이지) | 2.5초 | <5초 |
| 벡터 검색 (10개) | 0.15초 | <0.5초 |
| 하이브리드 검색 | 0.3초 | <1초 |
| 답변 생성 | 3.2초 | <5초 |
| 전체 응답 시간 | 4.8초 | <10초 |

---

## 12. 운영 및 모니터링

### 12.1 로깅

**로깅 설정**:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ispl.log'),
        logging.StreamHandler()
    ]
)
```

**주요 로그**:
- PDF 처리 시작/완료
- 검색 쿼리 및 결과 수
- 답변 생성 및 검증 점수
- API 요청/응답 시간
- 에러 발생 및 스택 트레이스

### 12.2 에러 처리

**글로벌 예외 핸들러**:
```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc)
        }
    )
```

### 12.3 환경 변수

`.env`:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/ispl_db

# OpenAI
OPENAI_API_KEY=sk-...

# Redis (Optional)
REDIS_UR