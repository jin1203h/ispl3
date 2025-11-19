# 보험약관 기반 Agentic AI 시스템 - 기술 연구 보고서 v2.0

**작성일**: 2025년 10월 27일  
**프로젝트명**: ISPL (Insurance Policy) - Agentic AI System  
**버전**: v2.0 (구현 완료 버전)

---

## 📋 문서 개요

본 문서는 실제 구현된 ISPL 시스템을 기반으로 작성된 기술 연구 보고서입니다. 초기 연구 보고서(v1.0)와 달리, 실제 구현 상태를 반영하여 아키텍처, 기술 스택, 구현 패턴, 성능 최적화 전략을 상세히 기술합니다.

---

## 1. 프로젝트 개요

### 1.1 목적
- 생성형 AI를 활용한 보험약관 전처리, 임베딩, 벡터DB 저장
- 자연어 질의에 대한 정확한 약관 검색 및 답변 제공
- 할루시네이션 방지 및 신뢰도 기반 답변 생성
- 파일 업로드 및 약관 통합 관리 기능 제공

### 1.2 프로젝트 범위
- **약관 업로드 및 전처리**: PDF → 하이브리드 전처리 → Markdown → 청킹 → 임베딩 → 벡터DB 저장
- **약관 검색**: 사용자 질의 전처리 → 하이브리드 검색(벡터+키워드) → 컨텍스트 최적화 → LLM 답변 생성 → 답변 검증
- **약관 관리**: 약관 목록 조회, 원본/Markdown 파일 다운로드/삭제, PDF 조회
- **대화 이력**: 세션별 대화 이력 저장 및 조회

### 1.3 주요 특징
- **LangGraph 기반 Multi-Agent 시스템**: 7개의 전문화된 에이전트로 구성
- **하이브리드 검색**: 벡터 검색(의미 기반) + 키워드 검색(정확한 매칭) 융합
- **답변 검증 시스템**: 4단계 검증(할루시네이션, 컨텍스트, 조항, 형식)으로 신뢰도 보장
- **청크 확장 메커니즘**: 컨텍스트 부족 시 자동으로 주변 청크 확장
- **Redis 캐싱**: 임베딩 결과 캐싱으로 API 비용 절감 및 성능 향상

### 1.4 제약 조건
- PoC 단계로 대규모 트래픽은 고려하지 않음
- 로컬 테스트 환경 우선
- PDF 파일만 지원 (다른 형식은 미지원)

---

## 2. 기술 스택

### 2.1 Backend
- **Framework**: FastAPI 0.115.0 (Python)
- **AI Framework**: 
  - LangGraph 0.3.27+ (Multi-Agent 워크플로우)
  - LangChain 0.3.7 (LLM 통합)
  - LangChain-OpenAI 0.2.8 (OpenAI 연동)
- **Database**: 
  - PostgreSQL 17.6 (메인 DB)
  - pgvector 0.3.6 (벡터 확장)
  - asyncpg 0.30.0 (비동기 드라이버)
  - SQLAlchemy 2.0.35 (ORM)
- **Cache**: Redis 5.2.1 (임베딩 캐시)
- **LLM**: 
  - OpenAI GPT-4o (답변 생성 및 Vision API)
  - Temperature: 0.1 (일관성 있는 답변)
- **Embedding**: OpenAI text-embedding-3-large (1536 차원)
- **PDF 처리**: 
  - PyMuPDF 1.24.14 (PDF 파싱)
  - pymupdf4llm 0.0.17 (Markdown 변환)
  - pdf2image 1.17.0 (이미지 변환)
  - GPT-4o Vision (이미지 기반 추출)
- **이미지 처리**:
  - OpenCV 4.10.0 (전처리)
  - Pillow 11.0.0 (이미지 조작)
- **유틸리티**:
  - tiktoken 0.8.0 (토큰 카운팅)
  - kiwipiepy 0.21.0 (한국어 형태소 분석)
  - tenacity 9.0.0 (재시도 로직)

### 2.2 Frontend
- **Framework**: Next.js 15.0.3 (App Router)
- **UI Library**: React 18.3.1
- **Language**: TypeScript 5.6.3
- **Styling**: Tailwind CSS 3.4.14
- **Markdown**: 
  - react-markdown 9.0.1
  - remark-gfm 4.0.0 (GitHub Flavored Markdown)

### 2.3 시스템 아키텍처

```
사용자 (브라우저)
    ↓
Next.js Frontend (포트 3000)
    ↓ HTTP/REST
FastAPI Backend (포트 8000)
    ↓
LangGraph Multi-Agent System
    ├─ Router Agent (라우팅)
    ├─ Search Agent (검색)
    ├─ Context Judgement Agent (컨텍스트 판단)
    ├─ Chunk Expansion Agent (청크 확장)
    ├─ Answer Agent (답변 생성)
    ├─ Processing Agent (PDF 전처리)
    └─ Management Agent (약관 관리)
    ↓
PostgreSQL + pgvector + Redis
    ↓
OpenAI API (GPT-4o, Embedding)
```

---

## 3. LangGraph Multi-Agent 아키텍처

### 3.1 Agent 구성 (7개)

#### 1. Router Agent (라우터)
- **역할**: 사용자 요청 분석 및 적절한 Agent로 라우팅
- **입력**: 사용자 질의
- **출력**: 의도 분류 및 Command 객체
- **라우팅 규칙**:
  - `search`: Search Agent로 전달 (검색 및 답변)
  - `upload`: Processing Agent로 전달 (PDF 처리)
  - `manage`: Management Agent로 전달 (약관 관리)

#### 2. Search Agent (검색)
- **역할**: 하이브리드 검색 수행
- **검색 방식**:
  - 벡터 검색 (의미 기반, Cosine Similarity)
  - 키워드 검색 (Full-Text Search)
  - RRF(Reciprocal Rank Fusion) 알고리즘으로 결과 융합
- **검색 범위**: 최대 20,000 토큰 (GPT-4o 컨텍스트)
- **유사도 임계값**: 0.65 (Cosine Similarity)
- **출력**: 검색된 청크 리스트

#### 3. Context Judgement Agent (컨텍스트 판단)
- **역할**: 검색된 컨텍스트가 질문에 답하기에 충분한지 판단
- **판단 기준**:
  - 청크 개수 (최소 3개 이상)
  - 내용 일치도
  - 조항 번호 존재 여부
- **출력**: 
  - `sufficient=True` → Answer Agent로 라우팅
  - `sufficient=False` → Chunk Expansion Agent로 라우팅

#### 4. Chunk Expansion Agent (청크 확장)
- **역할**: 컨텍스트 부족 시 주변 청크를 확장하여 추가
- **확장 전략**:
  - 같은 문서의 앞뒤 청크 확장 (±2 인덱스)
  - 같은 페이지의 청크 확장
  - 최대 3회까지 확장 시도
- **출력**: 확장된 청크 리스트
- **재판단**: Context Judgement Agent로 다시 전달

#### 5. Answer Agent (답변 생성)
- **역할**: LLM 기반 답변 생성 및 검증
- **모델**: GPT-4o (temperature: 0.1)
- **프롬프트**:
  - 시스템 프롬프트: 보험약관 전문 상담사 역할
  - 컨텍스트: 검색된 청크들
  - 사용자 질의
- **출력 형식**:
  ```
  📌 답변
  [답변 내용] [참조 1]
  
  📋 관련 약관
  [참조 1] 문서명 | 페이지 | 조항
  [내용]
  ```
- **검증**: AnswerValidator 서비스 호출

#### 6. Processing Agent (PDF 전처리)
- **역할**: PDF 업로드 및 하이브리드 전처리
- **처리 방식**:
  - `pymupdf`: PyMuPDF4LLM으로 빠른 텍스트 추출
  - `vision`: GPT-4o Vision으로 이미지 기반 추출
  - `both`: 하이브리드 방식 (기본값)
- **처리 단계**:
  1. PDF 업로드 및 메타데이터 저장
  2. Path 1 (PyMuPDF) 실행
  3. Path 2 (Vision API) 실행
  4. 결과 병합 (유사도 기반)
  5. 품질 검증
  6. 청킹 (1000 토큰, overlap 100)
  7. 임베딩 생성 (캐싱 활용)
  8. 벡터DB 저장
- **출력**: 처리 결과 및 품질 점수

#### 7. Management Agent (관리)
- **역할**: 약관 CRUD 작업
- **기능**:
  - 약관 목록 조회 (페이징, 필터링)
  - 약관 삭제 (문서 + 청크 + 파일)
  - 원본/Markdown 파일 다운로드
  - 약관 상세 정보 조회

### 3.2 LangGraph StateGraph 구조

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

builder = StateGraph(ISPLState)

# 노드 추가
builder.add_node("router", router_node)
builder.add_node("search_agent", search_node)
builder.add_node("context_judgement_agent", context_judgement_node)
builder.add_node("chunk_expansion_agent", chunk_expansion_node)
builder.add_node("answer_agent", answer_node)
builder.add_node("processing_agent", processing_node)
builder.add_node("management_agent", management_node)

# 엣지 정의
builder.add_edge(START, "router")
builder.add_edge("search_agent", "context_judgement_agent")

# 조건부 라우팅
def route_after_judgement(state: ISPLState) -> str:
    if state.get("context_sufficient", True):
        return "answer_agent"
    else:
        return "chunk_expansion_agent"

builder.add_conditional_edges(
    "context_judgement_agent",
    route_after_judgement,
    {
        "answer_agent": "answer_agent",
        "chunk_expansion_agent": "chunk_expansion_agent"
    }
)

builder.add_edge("chunk_expansion_agent", "context_judgement_agent")
builder.add_edge("answer_agent", END)
builder.add_edge("processing_agent", END)
builder.add_edge("management_agent", END)

# 메모리 체크포인트
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)
```

### 3.3 State 관리

```python
from langgraph.graph import MessagesState
from typing import TypedDict, List, Optional

class ISPLState(MessagesState):
    """ISPL LangGraph 상태"""
    query: str  # 사용자 질의
    next_agent: str  # 다음 에이전트
    task_type: str  # 작업 유형 (search/upload/manage)
    task_results: dict  # 작업 결과
    search_results: List[dict]  # 검색 결과
    final_answer: str  # 최종 답변
    error: Optional[str]  # 오류 메시지
    context_sufficient: Optional[bool]  # 컨텍스트 충분 여부
    expanded_chunks: List[dict]  # 확장된 청크
    expansion_count: int  # 확장 횟수
    chunks_to_expand: List[int]  # 확장할 청크 ID
```

---

## 4. FastAPI + PostgreSQL + pgvector 통합

### 4.1 Database 연결 패턴

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator

# 비동기 Engine 생성
engine = create_async_engine(
    f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}",
    echo=False,  # SQL 로깅
    pool_size=10,  # 연결 풀 크기
    max_overflow=20  # 최대 오버플로우
)

# Session Factory
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Dependency Injection
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
```

### 4.2 pgvector 벡터 검색

```python
from sqlalchemy import text

async def vector_search(
    session: AsyncSession,
    query_embedding: list[float],
    limit: int = 10,
    similarity_threshold: float = 0.65,
    document_ids: Optional[List[int]] = None
) -> List[VectorSearchResult]:
    """
    벡터 유사도 검색
    
    HNSW 인덱스를 사용한 코사인 유사도 검색
    """
    query = text("""
        SELECT 
            dc.id,
            dc.document_id,
            dc.chunk_index,
            dc.content,
            dc.page_number,
            dc.pdf_page_number,
            dc.clause_number,
            dc.section_title,
            dc.metadata,
            d.filename,
            d.original_filename,
            d.document_type,
            1 - (dc.embedding <=> :query_embedding) as similarity
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE 1 - (dc.embedding <=> :query_embedding) > :threshold
            AND d.status = 'active'
            AND (:document_ids::int[] IS NULL OR dc.document_id = ANY(:document_ids))
        ORDER BY dc.embedding <=> :query_embedding
        LIMIT :limit
    """)
    
    result = await session.execute(query, {
        "query_embedding": query_embedding,
        "threshold": similarity_threshold,
        "limit": limit,
        "document_ids": document_ids
    })
    
    return [VectorSearchResult(**row._mapping) for row in result.fetchall()]
```

### 4.3 Full-Text 키워드 검색

```python
async def keyword_search(
    session: AsyncSession,
    query: str,
    limit: int = 10
) -> List[dict]:
    """
    키워드 검색 (PostgreSQL Full-Text Search)
    
    사용: 조항 번호, 전문용어 등 정확한 매칭
    """
    # 키워드 추출 (조사 제거)
    keywords = extract_keywords(query)
    if not keywords:
        return []
    
    # tsquery 생성
    tsquery = ' & '.join(keywords)
    
    sql = text("""
        SELECT 
            dc.id,
            dc.document_id,
            dc.content,
            dc.page_number,
            dc.clause_number,
            d.filename,
            ts_rank(to_tsvector('simple', dc.content), 
                    to_tsquery('simple', :tsquery)) as rank
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE to_tsvector('simple', dc.content) @@ to_tsquery('simple', :tsquery)
            AND d.status = 'active'
        ORDER BY rank DESC
        LIMIT :limit
    """)
    
    result = await session.execute(sql, {
        "tsquery": tsquery,
        "limit": limit
    })
    
    return [dict(row._mapping) for row in result.fetchall()]
```

### 4.4 HNSW 인덱스 최적화

```sql
-- pgvector extension 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- HNSW 인덱스 생성
CREATE INDEX idx_chunks_embedding ON document_chunks 
USING hnsw (embedding vector_cosine_ops) 
WITH (
    m = 32,              -- 그래프 연결 수 (기본값: 16, 높을수록 정확하지만 느림)
    ef_construction = 200 -- 인덱스 구축 시 탐색 범위 (기본값: 64)
);

-- 인덱스 성능 모니터링
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,  -- 인덱스 스캔 횟수
    idx_tup_read,  -- 읽은 행 수
    idx_tup_fetch  -- 가져온 행 수
FROM pg_stat_user_indexes
WHERE indexname = 'idx_chunks_embedding';
```

---

## 5. PDF 하이브리드 전처리 파이프라인

### 5.1 전체 처리 흐름

```
PDF 입력
   ├─ 메타데이터 추출 (페이지 수, 제목 등)
   │
   ├─ Path 1: PyMuPDF4LLM
   │   ├─ 텍스트 직접 추출
   │   ├─ Markdown 변환
   │   └─ 구조화 (표, 이미지 감지)
   │
   ├─ Path 2: GPT-4o Vision (선택적)
   │   ├─ PDF → 고해상도 이미지 변환 (DPI 300)
   │   ├─ 이미지 전처리 (그레이스케일, 노이즈 제거)
   │   ├─ GPT-4o Vision API 호출
   │   └─ Markdown 결과 생성
   │
   ├─ 결과 병합 (유사도 기반)
   │   ├─ SequenceMatcher로 유사도 계산
   │   ├─ 중복 제거
   │   └─ 최적 결과 선택
   │
   ├─ 품질 검증
   │   ├─ 완전성 점수
   │   ├─ 일관성 검사
   │   └─ 신뢰도 평가
   │
   ├─ 청킹 (Fixed-size Chunking)
   │   ├─ Chunk Size: 1000 토큰
   │   ├─ Overlap: 100 토큰
   │   ├─ 특수 처리: 표(통째로), 이미지(설명+주변)
   │   └─ 메타데이터 부여 (페이지, 섹션, 조항)
   │
   ├─ 임베딩 생성
   │   ├─ OpenAI text-embedding-3-large
   │   ├─ 차원: 1536
   │   ├─ 배치 처리 (100개씩)
   │   └─ Redis 캐싱
   │
   └─ 벡터 DB 저장
       ├─ document_chunks 테이블
       ├─ HNSW 인덱스 자동 업데이트
       └─ 처리 로그 기록
```

### 5.2 Path 1: PyMuPDF4LLM 추출

```python
import pymupdf4llm

class PyMuPDFExtractor:
    """PyMuPDF4LLM을 사용한 PDF → Markdown 변환"""
    
    def extract(self, pdf_path: str) -> dict:
        """
        PDF에서 텍스트를 추출하고 Markdown으로 변환
        
        Returns:
            {
                'markdown': str,  # 변환된 Markdown
                'pages': int,     # 총 페이지 수
                'quality_score': float,  # 품질 점수
                'tables': List[dict],    # 감지된 표
                'images': List[dict]     # 감지된 이미지
            }
        """
        # PyMuPDF4LLM로 Markdown 변환
        md_text = pymupdf4llm.to_markdown(
            pdf_path,
            page_chunks=True,  # 페이지별 청킹
            write_images=True,  # 이미지 추출
            image_path="uploads/images",  # 이미지 저장 경로
            dpi=300  # 이미지 해상도
        )
        
        # 표 감지 (Markdown 테이블 구문)
        tables = self._detect_tables(md_text)
        
        # 이미지 감지 (![](path) 구문)
        images = self._detect_images(md_text)
        
        # 품질 점수 계산
        quality_score = self._calculate_quality(md_text, tables, images)
        
        return {
            'markdown': md_text,
            'pages': self._count_pages(pdf_path),
            'quality_score': quality_score,
            'tables': tables,
            'images': images
        }
```

### 5.3 Path 2: GPT-4o Vision 추출

```python
from pdf2image import convert_from_path
from openai import AsyncOpenAI
import base64

class VisionExtractor:
    """GPT-4o Vision을 사용한 PDF → Markdown 변환"""
    
    async def extract_async(self, pdf_path: str) -> dict:
        """
        PDF를 이미지로 변환 후 GPT-4o Vision으로 분석
        
        Returns:
            {
                'markdown': str,
                'pages': int,
                'quality_score': float,
                'api_calls': int,  # API 호출 횟수
                'total_cost': float  # 추정 비용
            }
        """
        # PDF → 이미지 변환 (DPI 300)
        images = convert_from_path(pdf_path, dpi=300, fmt='png')
        
        # 각 페이지를 Vision API로 처리
        page_results = []
        for idx, img in enumerate(images):
            # 이미지 전처리
            processed_img = self._preprocess_image(img)
            
            # Base64 인코딩
            img_base64 = self._encode_image(processed_img)
            
            # Vision API 호출
            markdown = await self._call_vision_api(img_base64, idx + 1)
            page_results.append(markdown)
        
        # 페이지 병합
        full_markdown = "\n\n---\n\n".join(page_results)
        
        return {
            'markdown': full_markdown,
            'pages': len(images),
            'quality_score': self._estimate_quality(full_markdown),
            'api_calls': len(images),
            'total_cost': self._estimate_cost(images)
        }
    
    async def _call_vision_api(self, img_base64: str, page_num: int) -> str:
        """GPT-4o Vision API 호출"""
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """이 보험 약관 페이지의 모든 내용을 Markdown 형식으로 변환해주세요.
                        
규칙:
1. 표는 Markdown 테이블로 변환
2. 이미지는 [이미지: 설명] 형식으로 표시
3. 조항 번호와 제목을 정확히 추출
4. 페이지 번호 정보 포함
5. 원본 레이아웃을 최대한 유지"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_base64}",
                            "detail": "high"  # 고해상도 분석
                        }
                    }
                ]
            }],
            max_tokens=4096,
            temperature=0.1  # 일관성 있는 변환
        )
        
        return response.choices[0].message.content
```

### 5.4 하이브리드 병합 전략

```python
from difflib import SequenceMatcher

class HybridMerger:
    """Path 1과 Path 2의 결과를 병합"""
    
    def merge(
        self,
        pymupdf_result: dict,
        vision_result: dict,
        threshold: float = 0.7
    ) -> dict:
        """
        유사도 기반 병합
        
        Args:
            pymupdf_result: PyMuPDF 결과
            vision_result: Vision 결과
            threshold: 유사도 임계값
        
        Returns:
            병합된 결과
        """
        # 페이지별로 분리
        pymupdf_pages = self._split_pages(pymupdf_result['markdown'])
        vision_pages = self._split_pages(vision_result['markdown'])
        
        merged_pages = []
        
        for idx, (p1, p2) in enumerate(zip(pymupdf_pages, vision_pages)):
            # 유사도 계산
            similarity = SequenceMatcher(None, p1, p2).ratio()
            
            if similarity >= threshold:
                # 유사도가 높으면 PyMuPDF 선택 (빠르고 정확)
                merged_pages.append(p1)
                logger.debug(f"페이지 {idx+1}: PyMuPDF 선택 (유사도={similarity:.2f})")
            else:
                # 유사도가 낮으면 Vision 선택 (표/이미지 처리 우수)
                merged_pages.append(p2)
                logger.debug(f"페이지 {idx+1}: Vision 선택 (유사도={similarity:.2f})")
        
        # 최종 병합
        merged_markdown = "\n\n---\n\n".join(merged_pages)
        
        return {
            'markdown': merged_markdown,
            'quality_score': self._calculate_merged_quality(
                pymupdf_result, vision_result
            )
        }
```

### 5.5 청킹 전략

```python
import tiktoken

class TextChunker:
    """텍스트를 고정 크기 청크로 분할"""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 100):
        """
        Args:
            chunk_size: 청크 크기 (토큰)
            overlap: 중첩 크기 (토큰)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def chunk(self, text: str, document_id: int) -> List[dict]:
        """
        텍스트를 청크로 분할
        
        Returns:
            청크 리스트 [
                {
                    'content': str,
                    'chunk_index': int,
                    'token_count': int,
                    'page_number': int,
                    'section_title': str,
                    'clause_number': str,
                    'metadata': dict
                },
                ...
            ]
        """
        # 표 분리 처리
        tables = self._extract_tables(text)
        
        # 표를 제외한 텍스트 청킹
        chunks = []
        tokens = self.encoding.encode(text)
        
        start = 0
        chunk_idx = 0
        
        while start < len(tokens):
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens)
            
            # 메타데이터 추출
            metadata = self._extract_metadata(chunk_text)
            
            chunks.append({
                'content': chunk_text,
                'chunk_index': chunk_idx,
                'token_count': len(chunk_tokens),
                'page_number': metadata.get('page_number'),
                'section_title': metadata.get('section_title'),
                'clause_number': metadata.get('clause_number'),
                'chunk_type': 'text',
                'metadata': metadata
            })
            
            chunk_idx += 1
            start = end - self.overlap  # 오버랩 적용
        
        # 표를 별도 청크로 추가
        for table in tables:
            chunks.append({
                'content': table['content'],
                'chunk_index': chunk_idx,
                'token_count': len(self.encoding.encode(table['content'])),
                'page_number': table.get('page_number'),
                'section_title': table.get('section_title'),
                'clause_number': None,
                'chunk_type': 'table',
                'metadata': table['metadata']
            })
            chunk_idx += 1
        
        return chunks
```

### 5.6 임베딩 생성 및 캐싱

```python
from openai import AsyncOpenAI
import hashlib
import redis.asyncio as redis

class EmbeddingService:
    """임베딩 생성 서비스 (Redis 캐싱)"""
    
    def __init__(self):
        self.client = AsyncOpenAI()
        self.redis = redis.from_url("redis://localhost:6379/0")
        self.model = "text-embedding-3-large"
        self.dimensions = 1536
    
    async def generate_embeddings(
        self,
        texts: List[str],
        use_cache: bool = True
    ) -> List[List[float]]:
        """
        배치로 임베딩 생성
        
        Args:
            texts: 텍스트 리스트
            use_cache: 캐시 사용 여부
        
        Returns:
            임베딩 벡터 리스트
        """
        if not texts:
            return []
        
        embeddings = []
        cache_misses = []
        
        # 캐시 확인
        if use_cache:
            for text in texts:
                cache_key = self._get_cache_key(text)
                cached = await self.redis.get(cache_key)
                
                if cached:
                    embeddings.append(json.loads(cached))
                    logger.debug(f"캐시 히트: {cache_key[:16]}...")
                else:
                    cache_misses.append(text)
                    embeddings.append(None)  # 플레이스홀더
        else:
            cache_misses = texts
            embeddings = [None] * len(texts)
        
        # 캐시 미스만 API 호출
        if cache_misses:
            logger.info(f"임베딩 생성: {len(cache_misses)}개 (캐시 미스)")
            
            response = await self.client.embeddings.create(
                model=self.model,
                input=cache_misses,
                dimensions=self.dimensions
            )
            
            # 결과 저장 및 캐싱
            miss_idx = 0
            for i, emb in enumerate(embeddings):
                if emb is None:  # 캐시 미스였던 항목
                    embedding = response.data[miss_idx].embedding
                    embeddings[i] = embedding
                    
                    # Redis에 캐싱 (TTL: 30일)
                    if use_cache:
                        cache_key = self._get_cache_key(cache_misses[miss_idx])
                        await self.redis.setex(
                            cache_key,
                            30 * 24 * 3600,  # 30일
                            json.dumps(embedding)
                        )
                    
                    miss_idx += 1
        
        return embeddings
    
    def _get_cache_key(self, text: str) -> str:
        """텍스트의 캐시 키 생성 (SHA-256 해시)"""
        return f"emb:{hashlib.sha256(text.encode()).hexdigest()}"
```

---

## 6. 하이브리드 검색 시스템

### 6.1 검색 전략

```python
class HybridSearchService:
    """벡터 검색 + 키워드 검색 융합"""
    
    RRF_K = 60  # RRF 파라미터
    MAX_CONTEXT_TOKENS = 20000  # GPT-4o 컨텍스트 제한
    
    async def hybrid_search(
        self,
        session: AsyncSession,
        query: str,
        limit: int = 10,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[dict]:
        """
        하이브리드 검색 수행
        
        Args:
            query: 검색 질의
            limit: 결과 개수
            vector_weight: 벡터 검색 가중치
            keyword_weight: 키워드 검색 가중치
        
        Returns:
            융합된 검색 결과
        """
        # 1. 질의 전처리
        preprocessed = self.preprocessor.preprocess(query)
        
        # 2. 벡터 검색 + 키워드 검색 병렬 실행
        vector_task = self.vector_search(
            session,
            preprocessed.expanded_query,
            limit=limit * 2
        )
        keyword_task = self.keyword_search(
            session,
            preprocessed.normalized_query,
            limit=limit * 2
        )
        
        vector_results, keyword_results = await asyncio.gather(
            vector_task,
            keyword_task
        )
        
        # 3. RRF 알고리즘으로 융합
        merged_results = self._rrf_merge(
            vector_results,
            keyword_results,
            vector_weight,
            keyword_weight
        )
        
        # 4. 컨텍스트 최적화 (토큰 제한)
        optimized_results = self._optimize_context(
            merged_results,
            max_tokens=self.MAX_CONTEXT_TOKENS
        )
        
        return optimized_results[:limit]
```

### 6.2 RRF (Reciprocal Rank Fusion) 알고리즘

```python
def _rrf_merge(
    self,
    vector_results: List[dict],
    keyword_results: List[dict],
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3
) -> List[dict]:
    """
    Reciprocal Rank Fusion으로 검색 결과 융합
    
    RRF 점수 = Σ (weight / (k + rank))
    
    Args:
        vector_results: 벡터 검색 결과
        keyword_results: 키워드 검색 결과
        vector_weight: 벡터 가중치
        keyword_weight: 키워드 가중치
    
    Returns:
        융합된 결과 (RRF 점수 기준 정렬)
    """
    scores = {}
    
    # 벡터 검색 점수
    for rank, result in enumerate(vector_results, start=1):
        chunk_id = result['id']
        rrf_score = vector_weight / (self.RRF_K + rank)
        
        if chunk_id not in scores:
            scores[chunk_id] = {
                'chunk_id': chunk_id,
                'data': result,
                'rrf_score': 0,
                'vector_rank': rank,
                'keyword_rank': None
            }
        
        scores[chunk_id]['rrf_score'] += rrf_score
    
    # 키워드 검색 점수
    for rank, result in enumerate(keyword_results, start=1):
        chunk_id = result['id']
        rrf_score = keyword_weight / (self.RRF_K + rank)
        
        if chunk_id not in scores:
            scores[chunk_id] = {
                'chunk_id': chunk_id,
                'data': result,
                'rrf_score': 0,
                'vector_rank': None,
                'keyword_rank': rank
            }
        else:
            scores[chunk_id]['keyword_rank'] = rank
        
        scores[chunk_id]['rrf_score'] += rrf_score
    
    # RRF 점수 기준 정렬
    sorted_results = sorted(
        scores.values(),
        key=lambda x: x['rrf_score'],
        reverse=True
    )
    
    # 데이터 추출
    return [item['data'] for item in sorted_results]
```

### 6.3 컨텍스트 최적화

```python
def _optimize_context(
    self,
    search_results: List[dict],
    max_tokens: int = 20000
) -> List[dict]:
    """
    토큰 제한 내에서 최적의 컨텍스트 선택
    
    Args:
        search_results: 검색 결과
        max_tokens: 최대 토큰 수
    
    Returns:
        최적화된 검색 결과
    """
    optimized = []
    total_tokens = 0
    
    for result in search_results:
        # 토큰 카운트
        chunk_tokens = len(self.encoding.encode(result['content']))
        
        if total_tokens + chunk_tokens > max_tokens:
            logger.debug(
                f"컨텍스트 최적화: {len(optimized)}개 청크, "
                f"{total_tokens} 토큰 (제한: {max_tokens})"
            )
            break
        
        optimized.append(result)
        total_tokens += chunk_tokens
    
    return optimized
```

---

## 7. 답변 검증 시스템

### 7.1 4단계 검증 프로세스

```python
class AnswerValidator:
    """답변 검증 서비스"""
    
    # 검증 가중치
    WEIGHTS = {
        "hallucination": 0.4,  # 할루시네이션 40%
        "context": 0.3,        # 컨텍스트 일치 30%
        "clause": 0.2,         # 조항 존재 20%
        "format": 0.1          # 형식 10%
    }
    
    async def validate(
        self,
        answer: str,
        query: str,
        search_results: List[dict],
        session: AsyncSession
    ) -> AnswerValidation:
        """
        답변 검증 (4단계)
        
        Returns:
            AnswerValidation 객체
        """
        # 1. 형식 검증
        format_validation = self._check_format(answer, search_results)
        
        # 2. 조항 존재 확인
        clause_validation = await self._check_clause_existence(
            answer, session
        )
        
        # 3. 컨텍스트 일치도
        context_validation = self._check_context_consistency(
            answer, search_results
        )
        
        # 4. 할루시네이션 검증 (GPT-4o)
        hallucination_validation = await self._check_hallucination(
            answer, query, search_results
        )
        
        # 종합 신뢰도 계산
        confidence = self._calculate_confidence(
            format_validation,
            clause_validation,
            context_validation,
            hallucination_validation
        )
        
        return AnswerValidation(
            confidence_score=confidence,
            is_valid=confidence >= 0.7,
            format_check=format_validation,
            clause_check=clause_validation,
            context_check=context_validation,
            hallucination_check=hallucination_validation
        )
```

### 7.2 할루시네이션 검증

```python
async def _check_hallucination(
    self,
    answer: str,
    query: str,
    search_results: List[dict]
) -> ValidationDetail:
    """
    GPT-4o를 사용한 할루시네이션 검증
    
    답변이 제공된 컨텍스트에만 기반했는지 확인
    """
    context = "\n\n".join([
        f"[청크 {i+1}]\n{r['content']}"
        for i, r in enumerate(search_results)
    ])
    
    prompt = f"""당신은 보험약관 답변 검증 전문가입니다.

질문: {query}

제공된 컨텍스트:
{context}

생성된 답변:
{answer}

검증 기준:
1. 답변의 모든 내용이 제공된 컨텍스트에 존재하는가?
2. 컨텍스트에 없는 정보를 추가하지 않았는가?
3. 추측이나 일반 상식을 사용하지 않았는가?

JSON 형식으로 응답하세요:
{{
    "is_grounded": true/false,
    "hallucinated_statements": ["문장1", "문장2", ...],
    "confidence": 0.0~1.0,
    "reason": "검증 이유"
}}"""

    response = await self.client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response.choices[0].message.content)
    
    return ValidationDetail(
        passed=result['is_grounded'],
        score=result['confidence'],
        details={
            'hallucinated_statements': result['hallucinated_statements'],
            'reason': result['reason']
        }
    )
```

### 7.3 조항 존재 확인

```python
async def _check_clause_existence(
    self,
    answer: str,
    session: AsyncSession
) -> ValidationDetail:
    """
    답변에 언급된 조항 번호가 실제로 DB에 존재하는지 확인
    """
    # 조항 번호 추출
    clause_pattern = r'제\s*(\d+)\s*조'
    clauses = re.findall(clause_pattern, answer)
    
    if not clauses:
        return ValidationDetail(
            passed=True,
            score=1.0,
            details={'message': '조항 번호 없음'}
        )
    
    # DB에서 조항 존재 확인
    existing_clauses = []
    missing_clauses = []
    
    for clause_num in clauses:
        query = text("""
            SELECT COUNT(*) as count
            FROM document_chunks
            WHERE clause_number LIKE :pattern
        """)
        
        result = await session.execute(
            query,
            {'pattern': f'%제{clause_num}조%'}
        )
        
        count = result.scalar()
        
        if count > 0:
            existing_clauses.append(clause_num)
        else:
            missing_clauses.append(clause_num)
    
    passed = len(missing_clauses) == 0
    score = len(existing_clauses) / len(clauses) if clauses else 1.0
    
    return ValidationDetail(
        passed=passed,
        score=score,
        details={
            'total_clauses': len(clauses),
            'existing_clauses': existing_clauses,
            'missing_clauses': missing_clauses
        }
    )
```

---

## 8. 질의 전처리 시스템

### 8.1 전처리 파이프라인

```python
class QueryPreprocessor:
    """사용자 질의 전처리"""
    
    def preprocess(self, query: str) -> PreprocessedQuery:
        """
        질의 전처리
        
        Returns:
            PreprocessedQuery(
                original_query: str,
                normalized_query: str,
                expanded_query: str,
                keywords: List[str],
                clause_numbers: List[str],
                is_incomplete: bool,
                suggestions: List[str]
            )
        """
        # 1. 정규화
        normalized = self._normalize(query)
        
        # 2. 전문용어 표준화
        standardized = self._standardize_terms(normalized)
        
        # 3. 동의어 확장
        expanded = self._expand_synonyms(standardized)
        
        # 4. 키워드 추출
        keywords = self._extract_keywords(expanded)
        
        # 5. 조항 번호 추출
        clause_numbers = self._extract_clause_numbers(normalized)
        
        # 6. 불완전 질의 감지
        is_incomplete, suggestions = self._detect_incomplete(normalized)
        
        return PreprocessedQuery(
            original_query=query,
            normalized_query=normalized,
            expanded_query=expanded,
            keywords=keywords,
            clause_numbers=clause_numbers,
            is_incomplete=is_incomplete,
            suggestions=suggestions
        )
```

### 8.2 전문용어 표준화

```python
def _standardize_terms(self, query: str) -> str:
    """
    보험 전문용어 표준화
    
    예: "암보험" → "암 보험"
         "보험료" → "보험료"
         "CI" → "중대한 질병"
    """
    standardized = query
    
    # 띄어�기 규칙 적용
    for wrong, correct in self.spacing_rules.items():
        standardized = standardized.replace(wrong, correct)
    
    # 약어 확장
    for abbr, full in self.abbreviations.items():
        # 단어 경계에서만 치환
        pattern = r'\b' + re.escape(abbr) + r'\b'
        standardized = re.sub(pattern, full, standardized, flags=re.IGNORECASE)
    
    return standardized
```

### 8.3 동의어 확장

```python
def _expand_synonyms(self, query: str) -> str:
    """
    동의어 확장
    
    예: "보험금" → "보험금 또는 급여금 또는 지급금"
    """
    expanded_terms = []
    
    words = query.split()
    
    for word in words:
        # 동의어 그룹 찾기
        synonyms = self._find_synonyms(word)
        
        if synonyms:
            # "word 또는 synonym1 또는 synonym2" 형식
            expanded = f"{word} {' '.join(['또는 ' + s for s in synonyms])}"
            expanded_terms.append(expanded)
        else:
            expanded_terms.append(word)
    
    return ' '.join(expanded_terms)
```

### 8.4 전문용어 사전 (insurance_terms.json)

```json
{
  "normalization": {
    "spacing": {
      "암보험": "암 보험",
      "건강보험": "건강 보험",
      "보험료": "보험료"
    }
  },
  "synonyms": {
    "보험금": ["급여금", "지급금", "보상금"],
    "계약자": ["가입자", "계약 당사자"],
    "피보험자": ["보험 대상자", "보험 가입자"],
    "수익자": ["보험금 수령인", "수취인"]
  },
  "abbreviations": {
    "CI": "중대한 질병",
    "TCM": "전통 의학",
    "MRI": "자기공명영상"
  },
  "incomplete_patterns": [
    {
      "pattern": "^(보장|보험금|청구|해지|면책)$",
      "suggestion": "구체적인 질문을 추가해주세요. 예: '보장 범위는?', '보험금은 언제?'"
    },
    {
      "pattern": "^\\w{1,3}$",
      "suggestion": "질문이 너무 짧습니다. 더 구체적으로 물어보세요."
    }
  ]
}
```

---

## 9. 청크 확장 메커니즘

### 9.1 확장 전략

```python
class ChunkExpansionService:
    """컨텍스트 부족 시 청크 확장"""
    
    MAX_EXPANSION_COUNT = 3  # 최대 확장 횟수
    
    async def expand_chunks(
        self,
        chunk_ids: List[int],
        session: AsyncSession,
        expansion_count: int
    ) -> List[dict]:
        """
        청크 확장
        
        전략:
        1. 같은 문서의 앞뒤 청크 (±2 인덱스)
        2. 같은 페이지의 청크
        3. 같은 섹션의 청크
        
        Args:
            chunk_ids: 확장할 청크 ID 리스트
            session: DB 세션
            expansion_count: 현재 확장 횟수
        
        Returns:
            확장된 청크 리스트
        """
        if expansion_count >= self.MAX_EXPANSION_COUNT:
            logger.warning(f"최대 확장 횟수 초과: {expansion_count}")
            return []
        
        expanded_chunks = []
        
        for chunk_id in chunk_ids:
            # 청크 정보 조회
            chunk = await self._get_chunk(session, chunk_id)
            if not chunk:
                continue
            
            # 전략 1: 앞뒤 청크
            neighbor_chunks = await self._get_neighbor_chunks(
                session,
                chunk['document_id'],
                chunk['chunk_index'],
                window=2
            )
            expanded_chunks.extend(neighbor_chunks)
            
            # 전략 2: 같은 페이지
            page_chunks = await self._get_page_chunks(
                session,
                chunk['document_id'],
                chunk['page_number']
            )
            expanded_chunks.extend(page_chunks)
            
            # 전략 3: 같은 섹션
            if chunk.get('section_title'):
                section_chunks = await self._get_section_chunks(
                    session,
                    chunk['document_id'],
                    chunk['section_title']
                )
                expanded_chunks.extend(section_chunks)
        
        # 중복 제거 및 정렬
        unique_chunks = self._deduplicate(expanded_chunks)
        
        logger.info(
            f"청크 확장 완료: {len(chunk_ids)}개 → {len(unique_chunks)}개 "
            f"(확장 횟수: {expansion_count + 1})"
        )
        
        return unique_chunks
```

### 9.2 앞뒤 청크 확장

```python
async def _get_neighbor_chunks(
    self,
    session: AsyncSession,
    document_id: int,
    chunk_index: int,
    window: int = 2
) -> List[dict]:
    """
    앞뒤 청크 가져오기
    
    예: chunk_index=10, window=2
    → chunk_index in [8, 9, 10, 11, 12]
    """
    query = text("""
        SELECT 
            id,
            document_id,
            chunk_index,
            content,
            page_number,
            section_title,
            clause_number
        FROM document_chunks
        WHERE document_id = :document_id
            AND chunk_index BETWEEN :start_idx AND :end_idx
        ORDER BY chunk_index
    """)
    
    result = await session.execute(query, {
        'document_id': document_id,
        'start_idx': chunk_index - window,
        'end_idx': chunk_index + window
    })
    
    return [dict(row._mapping) for row in result.fetchall()]
```

---

## 10. 대화 이력 관리

### 10.1 세션 기반 이력 관리

```python
class ChatHistoryService:
    """대화 이력 관리 서비스"""
    
    async def create_session(
        self,
        session: AsyncSession,
        user_id: Optional[int] = None
    ) -> ChatSession:
        """새 대화 세션 생성"""
        chat_session = ChatSession(
            user_id=user_id,
            session_id=str(uuid.uuid4()),
            created_at=datetime.utcnow()
        )
        
        session.add(chat_session)
        await session.commit()
        await session.refresh(chat_session)
        
        return chat_session
    
    async def add_message(
        self,
        session: AsyncSession,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> ChatMessage:
        """메시지 추가"""
        message = ChatMessage(
            session_id=session_id,
            role=role,  # 'user' or 'assistant'
            content=content,
            metadata=metadata,
            created_at=datetime.utcnow()
        )
        
        session.add(message)
        await session.commit()
        await session.refresh(message)
        
        return message
    
    async def get_session_history(
        self,
        session: AsyncSession,
        session_id: str,
        limit: int = 50
    ) -> List[ChatMessage]:
        """세션의 대화 이력 조회"""
        query = text("""
            SELECT *
            FROM chat_messages
            WHERE session_id = :session_id
            ORDER BY created_at ASC
            LIMIT :limit
        """)
        
        result = await session.execute(query, {
            'session_id': session_id,
            'limit': limit
        })
        
        return [ChatMessage(**row._mapping) for row in result.fetchall()]
```

---

## 11. API 엔드포인트

### 11.1 FastAPI 라우터 구조

```
backend/api/
  ├── health.py         # 헬스 체크
  ├── chat.py           # 챗봇 대화
  ├── chat_history.py   # 대화 이력
  ├── search.py         # 검색
  ├── documents.py      # 약관 관리
  └── pdf.py            # PDF 조회
```

### 11.2 주요 API

```python
# 1. 챗봇 대화
POST /api/chat
Request:
{
  "query": "골절 시 보장 여부는?",
  "session_id": "uuid",
  "stream": false
}
Response:
{
  "answer": "📌 답변\n...\n📋 관련 약관\n...",
  "search_results": [...],
  "validation": {
    "confidence_score": 0.85,
    "is_valid": true
  },
  "processing_time_ms": 1234
}

# 2. 스트리밍 대화
POST /api/chat/stream
Response: text/event-stream

# 3. 대화 이력 조회
GET /api/chat/history/{session_id}
Response:
{
  "session_id": "uuid",
  "messages": [
    {"role": "user", "content": "질문", "created_at": "..."},
    {"role": "assistant", "content": "답변", "created_at": "..."}
  ]
}

# 4. 약관 업로드
POST /api/documents/upload
Request: multipart/form-data
  file: PDF 파일
  document_type: "policy"
  insurance_type: "life"
Response:
{
  "document_id": 123,
  "filename": "상품명.pdf",
  "processing_status": "completed",
  "quality_score": 0.92,
  "chunks_count": 456
}

# 5. 약관 목록
GET /api/documents?page=1&limit=20
Response:
{
  "documents": [
    {
      "id": 123,
      "filename": "상품명.pdf",
      "document_type": "policy",
      "status": "active",
      "upload_timestamp": "...",
      "total_pages": 50
    }
  ],
  "total": 100,
  "page": 1,
  "pages": 5
}

# 6. 약관 삭제
DELETE /api/documents/{document_id}

# 7. PDF 조회
GET /api/pdf/{document_id}
Response: application/pdf

# 8. 검색
POST /api/search
Request:
{
  "query": "골절 보장",
  "limit": 10,
  "document_ids": [123, 456]
}
Response:
{
  "results": [
    {
      "chunk_id": 789,
      "content": "...",
      "similarity": 0.85,
      "document_name": "상품명.pdf",
      "page_number": 10
    }
  ]
}
```

---

## 12. Frontend 구조

### 12.1 Next.js App Router 구조

```
frontend/
  ├── app/
  │   ├── layout.tsx           # 루트 레이아웃
  │   ├── page.tsx             # 홈 (대시보드)
  │   ├── chat/
  │   │   └── page.tsx         # 챗봇 대화
  │   ├── documents/
  │   │   └── page.tsx         # 약관 관리
  │   └── history/
  │       └── page.tsx         # 대화 이력
  ├── components/
  │   ├── AppLayout.tsx        # 메인 레이아웃
  │   ├── Sidebar.tsx          # 사이드바
  │   ├── ChatMessage.tsx      # 챗 메시지
  │   ├── ChatInput.tsx        # 챗 입력
  │   ├── ChatHistory.tsx      # 대화 이력
  │   ├── DocumentUpload.tsx   # 약관 업로드
  │   ├── DocumentViewer.tsx   # 약관 조회
  │   ├── ReferencePanel.tsx   # 참조 패널
  │   └── DeleteConfirmDialog.tsx
  └── lib/
      └── api.ts               # API 클라이언트
```

### 12.2 주요 컴포넌트

```typescript
// ChatMessage.tsx - 챗 메시지 렌더링
export default function ChatMessage({ 
  message 
}: { 
  message: Message 
}) {
  return (
    <div className={`message ${message.role}`}>
      {message.role === 'assistant' ? (
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {message.content}
        </ReactMarkdown>
      ) : (
        <p>{message.content}</p>
      )}
    </div>
  );
}

// ChatInput.tsx - 챗 입력
export default function ChatInput({ 
  onSend 
}: { 
  onSend: (query: string) => void 
}) {
  const [query, setQuery] = useState('');
  
  const handleSubmit = () => {
    if (!query.trim()) return;
    onSend(query);
    setQuery('');
  };
  
  return (
    <div className="chat-input">
      <textarea
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="질문을 입력하세요..."
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
          }
        }}
      />
      <button onClick={handleSubmit}>전송</button>
    </div>
  );
}

// ReferencePanel.tsx - 참조 패널
export default function ReferencePanel({ 
  references 
}: { 
  references: Reference[] 
}) {
  return (
    <div className="reference-panel">
      <h3>📋 참조 문서</h3>
      {references.map((ref, idx) => (
        <div key={idx} className="reference-item">
          <div className="ref-header">
            [참조 {idx + 1}] {ref.filename}
          </div>
          <div className="ref-meta">
            페이지: {ref.page_number} | 
            유사도: {(ref.similarity * 100).toFixed(1)}%
          </div>
          <div className="ref-content">
            {ref.content.substring(0, 200)}...
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

## 13. 성능 최적화 전략

### 13.1 데이터베이스 최적화

```sql
-- 1. HNSW 인덱스 파라미터 튜닝
CREATE INDEX idx_chunks_embedding ON document_chunks 
USING hnsw (embedding vector_cosine_ops) 
WITH (
    m = 32,              -- 32로 증가 (기본값: 16)
    ef_construction = 200 -- 200으로 증가 (기본값: 64)
);

-- 2. 연결 풀 설정
-- SQLAlchemy Engine:
--   pool_size = 10
--   max_overflow = 20
--   pool_timeout = 30

-- 3. 쿼리 최적화
-- 복합 인덱스 추가
CREATE INDEX idx_chunks_document_page 
ON document_chunks(document_id, page_number);

CREATE INDEX idx_chunks_document_clause 
ON document_chunks(document_id, clause_number);

-- 4. VACUUM ANALYZE (정기적으로 실행)
VACUUM ANALYZE document_chunks;
```

### 13.2 Redis 캐싱 전략

```python
# 임베딩 캐싱
CACHE_KEY_PREFIX = "emb:"
CACHE_TTL = 30 * 24 * 3600  # 30일

# 캐시 히트율 모니터링
async def get_cache_stats(redis_client):
    info = await redis_client.info("stats")
    hits = info['keyspace_hits']
    misses = info['keyspace_misses']
    hit_rate = hits / (hits + misses) if (hits + misses) > 0 else 0
    
    logger.info(f"캐시 히트율: {hit_rate:.2%} (히트: {hits}, 미스: {misses})")
    
    return hit_rate
```

### 13.3 배치 처리

```python
# 임베딩 배치 처리 (100개씩)
BATCH_SIZE = 100

async def batch_embed(texts: List[str]) -> List[List[float]]:
    embeddings = []
    
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        batch_embeddings = await embedding_service.generate_embeddings(batch)
        embeddings.extend(batch_embeddings)
    
    return embeddings
```

### 13.4 비동기 처리

```python
# PDF 처리 비동기화
async def process_pdf_async(pdf_path: str, document_id: int):
    """백그라운드에서 PDF 처리"""
    # Path 1과 Path 2 병렬 실행
    pymupdf_task = asyncio.create_task(
        pymupdf_extractor.extract_async(pdf_path)
    )
    vision_task = asyncio.create_task(
        vision_extractor.extract_async(pdf_path)
    )
    
    pymupdf_result, vision_result = await asyncio.gather(
        pymupdf_task,
        vision_task
    )
    
    # 나머지 처리...
```

---

## 14. 모니터링 및 로깅

### 14.1 로깅 레벨

```python
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ispl.log'),
        logging.StreamHandler()
    ]
)

# 레벨별 사용
logger.debug("디버깅 정보")       # 개발 중
logger.info("정보 메시지")        # 정상 흐름
logger.warning("경고 메시지")     # 복구 가능한 문제
logger.error("오류 메시지")       # 처리 실패
logger.critical("심각한 오류")    # 시스템 장애
```

### 14.2 성능 메트릭

```python
# 처리 시간 측정
import time

start_time = time.time()
# ... 작업 수행 ...
processing_time = (time.time() - start_time) * 1000  # ms

logger.info(f"처리 완료: {processing_time:.2f}ms")

# 토큰 사용량 로깅
logger.info(
    f"임베딩 생성: {len(texts)}개 텍스트, "
    f"총 {total_tokens} 토큰, "
    f"비용: ${estimated_cost:.4f}"
)
```

---

## 15. 기술적 위험 요소 및 대응 방안

| 위험 요소 | 영향도 | 발생 가능성 | 대응 방안 | 현재 상태 |
|---------|-------|-----------|---------|---------|
| PDF 전처리 품질 저하 | 높음 | 중간 | 하이브리드 방식, 품질 검증 단계 추가 | ✅ 구현 완료 |
| LLM 할루시네이션 | 높음 | 높음 | 4단계 검증 시스템, 엄격한 프롬프트 | ✅ 구현 완료 |
| 벡터 검색 성능 저하 | 중간 | 중간 | HNSW 인덱스 최적화, 하이브리드 검색 | ✅ 구현 완료 |
| OpenAI API 비용 | 중간 | 높음 | Redis 캐싱, 배치 처리, 모니터링 | ✅ 구현 완료 |
| Multi-Agent 복잡도 | 중간 | 중간 | LangGraph 표준 패턴, 충분한 테스트 | ✅ 구현 완료 |
| 컨텍스트 부족 | 중간 | 중간 | 청크 확장 메커니즘 (최대 3회) | ✅ 구현 완료 |
| 데이터베이스 성능 | 낮음 | 낮음 | 연결 풀링, 인덱스 최적화 | ✅ 구현 완료 |

---

## 16. 라이브러리 버전 (구현 버전)

### Backend (requirements.txt)

```
# FastAPI 및 웹 프레임워크
fastapi==0.115.0
uvicorn[standard]==0.32.0
python-multipart==0.0.12

# 데이터베이스
sqlalchemy==2.0.35
asyncpg==0.30.0
psycopg2-binary==2.9.10
pgvector==0.3.6

# Redis (캐싱)
redis[hiredis]==5.2.1

# PDF 처리
PyMuPDF==1.24.14
pymupdf4llm==0.0.17
pdf2image==1.17.0
Pillow==11.0.0

# 이미지 처리
opencv-python==4.10.0.84
numpy>=1.26.0,<2.0.0

# OpenAI 및 LangChain
openai==1.55.3
tiktoken==0.8.0
tenacity==9.0.0

# LangChain 패키지
langchain==0.3.7
langchain-openai==0.2.8
langchain-community==0.3.5

# LangGraph
langgraph>=0.3.27

# 유틸리티
python-dotenv==1.0.1
pydantic==2.10.2
pydantic-settings==2.6.1

# 한글 처리
kiwipiepy=