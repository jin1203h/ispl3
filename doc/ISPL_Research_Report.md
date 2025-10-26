# 보험약관 기반 Agentic AI 시스템 - 기술 연구 보고서

**작성일**: 2025년 10월 14일  
**프로젝트명**: ISPL (Insurance Policy) - Agentic AI System

---

## 1. 프로젝트 개요

### 1.1 목적
- 생성형 AI를 활용하여 보험약관을 전처리, 요약, 임베딩 후 벡터DB에 저장
- 사용자의 자연어 질의에 대해 관련 약관을 검색하고 정확한 답변 제공
- 파일 업로드 및 약관 통합 관리 기능 제공

### 1.2 범위
- **약관 업로드 및 전처리**: PDF → 하이브리드 전처리 → Markdown → 임베딩 → 벡터DB 저장
- **약관 검색**: 사용자 질의 전처리 → 하이브리드 벡터 검색 → LLM 기반 답변 생성
- **약관 관리**: 저장된 약관 목록, 원본 파일 다운로드/삭제, PDF/Markdown 조회

### 1.3 제약 조건
- PoC 단계이므로 대규모 트래픽은 고려하지 않음
- 로컬 테스트 환경 우선
- 파일 형식: PDF만 지원

---

## 2. 기술 스택

### 2.1 Backend
- **Framework**: FastAPI (Python)
- **AI Framework**: LangGraph (Multi-Agent 시스템)
- **Database**: PostgreSQL 17.6 + pgvector extension
- **LLM**: OpenAI GPT-4
- **Embedding**: OpenAI text-embedding-3-large (1536 차원)
- **PDF 처리**: PyMuPDF4LLM, pdf2image, GPT-4 Vision

### 2.2 Frontend
- **Framework**: React/Next.js
- **Styling**: Tailwind CSS
- **UI 스타일**: Open Web UI 참고 (GPT 스타일 챗 인터페이스)

### 2.3 시스템 아키텍처

```
User → Frontend (React/Next.js)
         ↓
    FastAPI Backend
         ↓
   LangGraph Multi-Agent System
    ├─ Router Agent (라우팅)
    ├─ Processing Agent (PDF 전처리)
    ├─ Search Agent (벡터 검색)
    ├─ Answer Agent (답변 생성)
    └─ Management Agent (약관 관리)
         ↓
  PostgreSQL + pgvector
```

---

## 3. LangGraph Multi-Agent 아키텍처

### 3.1 Agent 구성

**1. Router Agent (라우터)**
- 역할: 사용자 요청 분석 및 적절한 Agent로 라우팅
- 기술: LangGraph Command 객체 사용
- 의도 분류: search/upload/manage

**2. Processing Agent (전처리)**
- 역할: PDF 업로드 및 하이브리드 전처리 담당
- 처리 방식: Path 1 (PyMuPDF4LLM) + Path 2 (GPT-4 Vision) 병렬 실행
- 출력: 통합된 Markdown 문서 + 품질 검증 결과

**3. Search Agent (검색)**
- 역할: 하이브리드 검색 (벡터 + 키워드) 수행
- 검색 범위: 컨텍스트 최적화 (최대 8000 토큰)
- 유사도 임계값: 0.7 이상 (Cosine Similarity)

**4. Answer Agent (답변)**
- 역할: LLM 기반 답변 생성 및 검증
- 모델: GPT-4 (temperature: 0.1)
- 검증: 할루시네이션 방지 로직 포함

**5. Management Agent (관리)**
- 역할: 약관 목록 조회, 삭제, 다운로드
- 기능: CRUD 작업 전담

### 3.2 LangGraph 구현 패턴

```python
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.types import Command
from typing import Literal

# State 정의
class ISPLState(MessagesState):
    next_agent: str
    task_type: str
    task_results: dict

# Supervisor Pattern Graph 구성
builder = StateGraph(ISPLState)
builder.add_node("router", router_agent)
builder.add_node("processing_agent", processing_agent)
builder.add_node("search_agent", search_agent)
builder.add_node("answer_agent", answer_agent)
builder.add_node("management_agent", management_agent)

# Edge 설정
builder.add_edge(START, "router")
builder.add_edge("processing_agent", "router")
builder.add_edge("search_agent", "answer_agent")
builder.add_edge("answer_agent", END)
builder.add_edge("management_agent", END)

graph = builder.compile()
```

---

## 4. FastAPI + PostgreSQL + pgvector 통합

### 4.1 Database 연결 패턴

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from fastapi import Depends
from typing import Annotated

# 비동기 Engine 생성
engine = create_async_engine(
    "postgresql+asyncpg://user:password@localhost/ispl_db",
    echo=True
)

# Session Factory
async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# 의존성 주입을 위한 Session Dependency
async def get_session():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

SessionDep = Annotated[AsyncSession, Depends(get_session)]
```

### 4.2 pgvector 벡터 검색

```python
from sqlalchemy import text

async def search_vectors(
    query_embedding: list[float],
    session: SessionDep,
    limit: int = 10,
    similarity_threshold: float = 0.7
):
    query = text("""
        SELECT 
            id, content, metadata,
            1 - (embedding <=> :query_embedding) as similarity
        FROM document_chunks
        WHERE 1 - (embedding <=> :query_embedding) > :threshold
        ORDER BY embedding <=> :query_embedding
        LIMIT :limit
    """)
    
    result = await session.execute(query, {
        "query_embedding": query_embedding,
        "threshold": similarity_threshold,
        "limit": limit
    })
    
    return result.fetchall()
```

### 4.3 HNSW 인덱스 설정

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE INDEX idx_chunks_embedding ON document_chunks 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 32, ef_construction = 200);
```

---

## 5. PDF 하이브리드 전처리 파이프라인

### 5.1 처리 흐름

```
PDF 입력
   ├─ Path 1: PyMuPDF4LLM (직접 텍스트 추출)
   │    └─ Markdown 변환
   │
   └─ Path 2: GPT-4 Vision (이미지 기반)
        ├─ pdf2image로 고해상도 이미지 변환 (DPI 300)
        ├─ 이미지 전처리 (그레이스케일, 노이즈 제거)
        └─ GPT-4 Vision API 호출
   
결과 병합 (유사도 기반)
   ↓
품질 검증
   ↓
청킹 (1000 토큰, overlap 100)
   ↓
임베딩 생성 (text-embedding-3-large, 1536차원)
   ↓
벡터 DB 저장
```

### 5.2 Path 1: PyMuPDF4LLM

```python
import pymupdf4llm

def extract_with_pymupdf(pdf_path: str) -> str:
    """PyMuPDF4LLM을 사용한 Markdown 변환"""
    md_text = pymupdf4llm.to_markdown(pdf_path)
    return md_text
```

### 5.3 Path 2: GPT-4 Vision

```python
from pdf2image import convert_from_path
from openai import OpenAI

def extract_with_vision(pdf_path: str) -> str:
    """GPT-4 Vision을 사용한 이미지 기반 추출"""
    # PDF를 이미지로 변환 (DPI 300)
    images = convert_from_path(pdf_path, dpi=300)
    
    client = OpenAI()
    results = []
    
    for img in images:
        img_base64 = encode_image(img)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "이 보험 약관 페이지의 모든 텍스트, 표, 이미지를 Markdown 형식으로 변환해주세요."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
                ]
            }]
        )
        results.append(response.choices[0].message.content)
    
    return "\n\n".join(results)
```

---

## 6. 벡터 검색 및 임베딩

### 6.1 청킹 전략

- **방식**: Fixed-size Chunking
- **Chunk Size**: 1,000 토큰
- **Overlap**: 50-100 토큰
- **특수 처리**:
  - 표: 전체 표 단위로 하나의 chunk
  - 이미지: 설명 + 주변 텍스트 (200-400 토큰)

```python
def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    """Fixed-size chunking with overlap"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    
    return chunks
```

### 6.2 OpenAI Embedding

```python
from openai import OpenAI

def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """text-embedding-3-large로 임베딩 생성 (1536 차원)"""
    client = OpenAI()
    
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=texts
    )
    
    return [item.embedding for item in response.data]
```

### 6.3 하이브리드 검색

- **벡터 검색**: 코사인 유사도 기반
- **키워드 검색**: 전문용어, 조항 번호 등
- **결과 융합**: 유사도 점수와 키워드 매칭 점수 결합

---

## 7. 할루시네이션 방지 전략

### 7.1 시스템 프롬프트

```
당신은 보험약관 전문 상담사입니다. 다음 규칙을 반드시 준수하세요:

1. 정확성 보장: 제공된 약관 내용에만 기반하여 답변하세요.
2. 근거 제시: 모든 답변에 해당 약관 조항을 인용하세요.
3. 한계 인정: 제공된 자료에 없는 내용은 "해당 정보가 약관에 명시되어 있지 않습니다"라고 답하세요.
4. 명확한 구조: 답변을 ①직접 답변 ②관련 약관 ③주의사항 순으로 구성하세요.
5. 금지사항: 추측, 일반 상식, 다른 보험사 정보는 절대 사용하지 마세요.
```

### 7.2 검증 로직

- 응답에 반드시 약관 조항 번호 인용
- 생성 답변을 원본 컨텍스트와 재대조
- 신뢰도 점수 계산 (0.7 이하 시 재생성)

---

## 8. 기술적 위험 요소 및 대응 방안

| 위험 요소 | 영향도 | 발생 가능성 | 대응 방안 |
|---------|-------|-----------|---------|
| PDF 전처리 품질 저하 | 높음 | 중간 | 하이브리드 방식, 품질 검증 단계 추가 |
| LLM 할루시네이션 | 높음 | 높음 | 엄격한 프롬프트, 실시간 검증 |
| 벡터 검색 성능 저하 | 중간 | 중간 | HNSW 인덱스 최적화, 캐싱 |
| OpenAI API 비용 | 중간 | 높음 | 배치 처리, 캐싱, 모니터링 |
| Multi-Agent 복잡도 | 중간 | 중간 | 단계별 구현, 충분한 테스트 |

---

## 9. 권장 라이브러리 버전

### Backend
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.0
asyncpg==0.29.0
pgvector==0.3.0
pymupdf4llm==0.1.0
pdf2image==1.17.0
openai==1.40.0
langgraph==0.2.74
langchain==0.2.0
pydantic==2.8.0
```

### Frontend
```
next==15.0.0
react==19.0.0
typescript==5.5.0
tailwindcss==3.4.0
```

---

## 10. 결론

본 연구를 통해 보험약관 기반 Agentic AI 시스템 구축에 필요한 모든 기술 스택과 아키텍처를 상세히 분석했습니다. 

**핵심 성공 요소:**
1. LangGraph Multi-Agent 시스템을 통한 유연한 워크플로우
2. 하이브리드 PDF 전처리로 높은 텍스트 추출 품질
3. pgvector HNSW 인덱스를 활용한 빠른 벡터 검색
4. 엄격한 프롬프트와 검증 로직으로 할루시네이션 방지
5. FastAPI + React/Next.js로 현대적이고 확장 가능한 시스템

이제 이 연구 결과를 기반으로 상세 작업 계획을 수립하고 체계적으로 개발을 진행할 수 있습니다.

