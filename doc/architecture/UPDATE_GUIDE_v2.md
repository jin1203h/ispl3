# ISPL 아키텍처 다이어그램 v2 업데이트 가이드

**작성일**: 2025년 10월 27일  
**목적**: 실제 구현된 시스템을 반영하여 아키텍처 다이어그램 업데이트

---

## 📋 업데이트 필요 사항 요약

### 1. 02_langgraph_agents_v2.svg - 7개 에이전트 시스템

**기존 (5개 에이전트)**:
1. Router Agent
2. Search Agent
3. Answer Agent
4. Processing Agent
5. Management Agent

**업데이트 (7개 에이전트)**:
1. Router Agent (유지)
2. Search Agent (유지, 기능 강화)
3. **Context Judgement Agent** ⭐ NEW
4. **Chunk Expansion Agent** ⭐ NEW
5. Answer Agent (유지, 검증 강화)
6. Processing Agent (유지)
7. Management Agent (유지)

**새로운 워크플로우**:
```
사용자 요청
    ↓
Router Agent
    ├─ [search] → Search Agent
    │              ↓
    │         Context Judgement Agent
    │              ├─ [충분] → Answer Agent → END
    │              └─ [불충분] → Chunk Expansion Agent
    │                              ↓
    │                         Context Judgement Agent (재판단)
    │
    ├─ [upload] → Processing Agent → END
    │
    └─ [manage] → Management Agent → END
```

**주요 변경사항**:
- Context Judgement Agent 추가 (컨텍스트 충분성 판단)
- Chunk Expansion Agent 추가 (동적 청크 확장)
- Search Agent 다음에 조건부 라우팅 추가
- 재판단 루프 추가

---

### 2. 03_pdf_processing_pipeline_v2.svg - PDF 처리 파이프라인

**주요 업데이트**:

1. **Quality Validation 단계 추가** ⭐ NEW
   - HybridMerger 다음에 QualityValidator 추가
   - 완전성/일관성/정확도 검사
   - 품질 점수 산출

2. **EmbeddingCache 표시** ⭐ NEW
   - Embedding 단계에 캐싱 표시 (MemoryCache 사용)
   - content_hash 기반 중복 제거

3. **처리 시간 표시**:
   - PyMuPDF: ~5-10초 (10페이지)
   - Vision: ~30-60초 (10페이지)
   - Hybrid: ~40-70초 (10페이지)

4. **서비스 컴포넌트 명시**:
   - PyMuPDFExtractor
   - VisionExtractor
   - HybridMerger
   - QualityValidator
   - TextChunker
   - EmbeddingService
   - EmbeddingCache

---

### 3. 04_search_answer_flow_v2.svg - 검색 및 답변 플로우

**주요 업데이트**:

1. **Query 전처리 추가** ⭐ NEW (3단계 확장)
   - QueryPreprocessor 서비스
   - 정규화 → 표준화 → 키워드 추출

2. **하이브리드 검색 상세화** ⭐ ENHANCED (4단계 확장)
   - 벡터 검색 (VectorSearchService)
   - 키워드 검색 (tsquery)
   - RRF 융합 (K=60)
   - 컨텍스트 최적화 (20K 토큰)

3. **컨텍스트 판단 및 확장 추가** ⭐ NEW
   - Context Judgement Agent
   - Chunk Expansion Agent
   - 재판단 루프

4. **4단계 검증 추가** ⭐ NEW (9단계 확장)
   - AnswerValidator 서비스
   - 형식 검증 (10%)
   - 조항 검증 (20%)
   - 컨텍스트 일치도 (30%)
   - 할루시네이션 검증 (40%)
   - 신뢰도 계산 및 재생성 로직

**전체 플로우 (기존 8단계 → 14단계)**:
1. 사용자 질문
2. 의도 분석 (Router Agent)
3. **Query 전처리 (QueryPreprocessor)** ⭐ NEW
4. **하이브리드 검색 (HybridSearchService)** ⭐ ENHANCED
   - 4-1. 벡터 검색
   - 4-2. 키워드 검색
   - 4-3. RRF 융합
   - 4-4. 컨텍스트 최적화
5. **컨텍스트 판단 (Context Judgement)** ⭐ NEW
6. **청크 확장 (Chunk Expansion, 필요 시)** ⭐ NEW
7. 답변 생성 (Answer Agent)
8. **4단계 검증 (AnswerValidator)** ⭐ NEW
   - 8-1. 형식 검증
   - 8-2. 조항 검증
   - 8-3. 컨텍스트 일치도
   - 8-4. 할루시네이션 검증
9. 응답 반환

---

### 4. 05_database_schema_v2.svg - 데이터베이스 스키마

**주요 업데이트**:

1. **document_chunks 테이블 필드 추가** ⭐ NEW
   - `pdf_page_number INTEGER` (PDF 내부 인쇄 페이지 번호)
   - 기존: `page_number` (Vision의 물리적 순서)
   - 인덱스 추가: `idx_chunks_pdf_page`

2. **chat_sessions 테이블 추가** ⭐ NEW
   ```
   chat_sessions
   - id SERIAL PRIMARY KEY
   - user_id INTEGER REFERENCES users(id)
   - title VARCHAR(255)
   - created_at TIMESTAMP
   - updated_at TIMESTAMP
   ```

3. **chat_messages 테이블 추가** ⭐ NEW
   ```
   chat_messages
   - id SERIAL PRIMARY KEY
   - session_id INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE
   - role VARCHAR(20) (user/assistant)
   - content TEXT
   - metadata JSONB
   - created_at TIMESTAMP
   ```

4. **관계 추가**:
   - users ← chat_sessions (1:N)
   - chat_sessions ← chat_messages (1:N, CASCADE)

5. **인덱스 추가**:
   - idx_chunks_pdf_page
   - idx_chat_messages_session_id

---

### 5. 06_tech_stack_v2.svg - 기술 스택

**주요 업데이트 (실제 버전 반영)**:

**Frontend**:
- Next.js **15.0.3** (기존: 15)
- React **18.3.1** (기존: 18)
- TypeScript **5.6.3** (기존: 5.5)
- Tailwind CSS **3.4.14** (기존: 3.4)
- **react-markdown 9.0.1** ⭐ NEW
- **remark-gfm 4.0.0** ⭐ NEW

**Backend**:
- FastAPI **0.115.0** (기존: 0.115.0)
- uvicorn **0.32.0** (기존: 0.30.0)
- SQLAlchemy **2.0.35** (기존: 2.0.0)
- Pydantic **2.10.2** (기존: 2.8.0)
- LangGraph **0.3.27+** (기존: 0.2.74)
- LangChain **0.3.7** (기존: 0.2.0)

**AI/ML**:
- **GPT-4o** (gpt-4o) ⭐ UPDATED (기존: GPT-4)
- **GPT-4o Vision** ⭐ UPDATED (기존: GPT-4 Vision)
- OpenAI SDK **1.55.3** (기존: 1.40.0)

**Data Processing**:
- PyMuPDF **1.24.14** (기존: 1.24.x)
- pymupdf4llm **0.0.17** (기존: 0.1.0)
- **OpenCV 4.10.0.84** ⭐ NEW
- **Pillow 11.0.0** ⭐ NEW
- **kiwipiepy 0.21.0** ⭐ NEW (한글 형태소 분석, py-hanspell 대체)
- tiktoken **0.8.0** (기존: 0.8.0)
- **tenacity 9.0.0** ⭐ NEW (재시도 로직)

**Database**:
- PostgreSQL **17.6** (기존: 17.6)
- pgvector **0.3.6** (기존: 0.3.0)
- asyncpg **0.30.0** (기존: 0.29.0)

**Cache**:
- Redis **5.2.1** (기존: 버전 미명시)

**제거된 항목**:
- ~~py-hanspell~~ (Python 3.13 호환 문제로 제거)
- ~~Shadcn/ui~~ (Frontend에서 미사용)

---

### 6. 01_system_overview_v2.svg - 시스템 개요

**주요 업데이트**:

1. **LangGraph 에이전트 수 변경**:
   - "5 Agents" → "7 Agents"

2. **Redis 캐싱 표시** ⭐ NEW:
   - Embedding Cache
   - 점선으로 선택사항 표시

3. **데이터 흐름 상세화**:
   - Frontend ← → Backend (REST API)
   - Backend ← → LangGraph (Multi-Agent)
   - LangGraph ← → PostgreSQL (SQL)
   - LangGraph ← → OpenAI API (HTTP)
   - LangGraph ← → Redis (Cache)

---

## 🎨 SVG 업데이트 가이드

### 공통 스타일 업데이트

**색상 팔레트**:
```css
.new-feature { fill: #d4edda; stroke: #28a745; } /* 신규 기능 - 녹색 */
.enhanced { fill: #fff3cd; stroke: #ffc107; } /* 개선 기능 - 노란색 */
.agent { fill: #d1ecf1; stroke: #0c5460; } /* 에이전트 - 청록색 */
.service { fill: #f8d7da; stroke: #721c24; } /* 서비스 - 분홍색 */
```

**아이콘**:
- ⭐ 신규 기능
- 🔄 업데이트된 기능
- 🔍 검색 관련
- 💾 저장 관련
- ⚡ 성능 관련
- 🔒 검증 관련

### 텍스트 크기

```css
.title { font: bold 24px sans-serif; }
.subtitle { font: bold 16px sans-serif; }
.text { font: 14px sans-serif; }
.small-text { font: 12px sans-serif; }
.version-badge { font: bold 11px sans-serif; }
```

---

## 📝 업데이트 체크리스트

### 02_langgraph_agents_v2.svg
- [ ] Context Judgement Agent 추가
- [ ] Chunk Expansion Agent 추가
- [ ] 조건부 라우팅 화살표 추가
- [ ] 재판단 루프 표시
- [ ] 에이전트 수 5→7 변경

### 03_pdf_processing_pipeline_v2.svg
- [ ] QualityValidator 단계 추가
- [ ] EmbeddingCache 표시
- [ ] 처리 시간 표시
- [ ] 서비스 컴포넌트 명시

### 04_search_answer_flow_v2.svg
- [ ] QueryPreprocessor 추가
- [ ] 하이브리드 검색 4단계 표시
- [ ] Context Judgement 추가
- [ ] Chunk Expansion 추가
- [ ] 4단계 검증 표시
- [ ] 단계 수 8→14 변경

### 05_database_schema_v2.svg
- [ ] pdf_page_number 필드 추가
- [ ] chat_sessions 테이블 추가
- [ ] chat_messages 테이블 추가
- [ ] 관계 화살표 추가
- [ ] 인덱스 추가

### 06_tech_stack_v2.svg
- [ ] 모든 버전 번호 업데이트
- [ ] 신규 라이브러리 추가 (react-markdown, remark-gfm, etc.)
- [ ] 제거된 라이브러리 삭제
- [ ] GPT-4 → GPT-4o 변경

### 01_system_overview_v2.svg
- [ ] "5 Agents" → "7 Agents"
- [ ] Redis 캐싱 표시
- [ ] 데이터 흐름 상세화

---

## 🔧 수동 업데이트 방법

각 SVG 파일을 텍스트 에디터로 열어 다음을 수행:

1. **파일 복사**:
   ```bash
   cp 02_langgraph_agents.svg 02_langgraph_agents_v2.svg
   ```

2. **제목 업데이트**:
   ```xml
   <text>LangGraph Multi-Agent 상세 구조</text>
   →
   <text>LangGraph Multi-Agent 상세 구조 v2</text>
   ```

3. **요소 추가**:
   - 새 `<rect>` 요소로 박스 추가
   - 새 `<text>` 요소로 텍스트 추가
   - 새 `<path>` 요소로 화살표 추가

4. **viewBox 조정** (필요 시):
   ```xml
   viewBox="0 0 1400 1000"
   →
   viewBox="0 0 1400 1200"  <!-- 높이 증가 -->
   ```

---

## 📊 우선순위

**높음** (필수):
1. ✅ README_v2.md (완료)
2. 02_langgraph_agents_v2.svg (7개 에이전트)
3. 04_search_answer_flow_v2.svg (검색 플로우)

**중간** (권장):
4. 05_database_schema_v2.svg (스키마)
5. 06_tech_stack_v2.svg (기술 스택)

**낮음** (선택):
6. 03_pdf_processing_pipeline_v2.svg (PDF 처리)
7. 01_system_overview_v2.svg (시스템 개요)

---

## 📚 참고 자료

- 실제 구현 코드:
  - `backend/agents/` - 에이전트 구현
  - `backend/services/` - 서비스 구현
  - `backend/database/schema.sql` - 스키마
  - `backend/requirements.txt` - 의존성

- 문서:
  - `doc/ISPL_Research_Report_v2.md` - 기술 연구 보고서
  - `doc/Insurance Policy_prd.md` - PRD

---

**마지막 업데이트**: 2025년 10월 27일  
**작성자**: ISPL 개발팀

