# ISPL 프로젝트 - 상세 작업 계획

**작성일**: 2025년 10월 14일  
**프로젝트명**: ISPL (Insurance Policy) - Agentic AI System  
**총 예상 기간**: 14주 (약 3.5개월)

---

## 개발 로드맵

### Phase 1: 기본 인프라 구축 (2주)

#### Task 1.1: 프로젝트 초기 설정
**목표**: 개발 환경 및 프로젝트 구조 설정

**세부 작업**:
- Python 가상환경 생성 및 의존성 관리 (requirements.txt)
- Git 저장소 초기화 및 .gitignore 설정
- 프로젝트 디렉토리 구조 생성
  ```
  backend/
    ├── app/
    │   ├── agents/      # LangGraph agents
    │   ├── api/         # FastAPI routes
    │   ├── core/        # 설정, 유틸리티
    │   ├── models/      # SQLAlchemy 모델
    │   └── services/    # 비즈니스 로직
    ├── tests/
    └── requirements.txt
  
  frontend/
    ├── app/
    ├── components/
    └── package.json
  
  doc/
  uploads/
  ```
- 환경 변수 설정 (.env.example 생성)

**완료 기준**:
- 프로젝트 구조가 PRD 명세대로 구성됨
- 의존성 파일이 준비되고 설치 가능
- README.md에 설치 및 실행 방법 문서화

**예상 소요 시간**: 2일

---

#### Task 1.2: PostgreSQL + pgvector 설정
**목표**: 데이터베이스 및 벡터 검색 환경 구축

**세부 작업**:
- PostgreSQL 17.6 설치 및 데이터베이스 생성
- pgvector extension 설치
- schema.sql 작성 (PRD 7장 참고)
  - users 테이블
  - documents 테이블
  - document_chunks 테이블 (VECTOR(1536) 컬럼 포함)
  - processing_logs 테이블
  - search_logs 테이블
- HNSW 인덱스 생성
  ```sql
  CREATE INDEX idx_chunks_embedding ON document_chunks 
  USING hnsw (embedding vector_cosine_ops) 
  WITH (m = 32, ef_construction = 200);
  ```

**완료 기준**:
- PostgreSQL이 정상 동작
- pgvector extension이 설치되고 벡터 검색 테스트 성공
- 모든 테이블과 인덱스가 생성됨

**예상 소요 시간**: 3일

---

#### Task 1.3: FastAPI 기본 구조 및 Database 연결
**목표**: FastAPI 애플리케이션 기본 구조 및 비동기 DB 연결 구현

**세부 작업**:
- FastAPI 앱 초기화 (main.py)
- SQLAlchemy 비동기 엔진 설정
  ```python
  from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
  
  engine = create_async_engine(
      "postgresql+asyncpg://user:password@localhost/ispl_db",
      echo=True
  )
  ```
- 의존성 주입 패턴 구현 (SessionDep)
- 기본 헬스체크 엔드포인트 생성 (`/health`)
- SQLAlchemy 모델 정의 (Documents, DocumentChunks 등)
- Pydantic 스키마 정의 (요청/응답 모델)

**완료 기준**:
- FastAPI 서버가 정상 실행됨
- DB 연결이 정상 동작
- 헬스체크 엔드포인트가 응답함
- ORM 모델이 DB 스키마와 일치

**예상 소요 시간**: 3일

---

#### Task 1.4: Next.js 프로젝트 초기화 및 기본 레이아웃
**목표**: Frontend 프로젝트 설정 및 기본 UI 레이아웃 구축

**세부 작업**:
- Next.js 15 + TypeScript 프로젝트 생성
- Tailwind CSS 설정
- 기본 레이아웃 컴포넌트 생성
  - Header
  - Sidebar (최근 대화 목록)
  - Main Content Area
- 라우팅 구조 설정
  - `/` (메인 채팅 페이지)
  - `/documents` (약관 관리 페이지)
- axios 또는 fetch를 사용한 API 클라이언트 설정

**완료 기준**:
- Next.js 개발 서버가 정상 실행됨
- 기본 레이아웃이 렌더링됨
- 라우팅이 동작함

**예상 소요 시간**: 2일

---

### Phase 2: PDF 전처리 시스템 (3주)

#### Task 2.1: PyMuPDF4LLM 통합 (Path 1)
**목표**: PDF에서 직접 텍스트를 추출하여 Markdown으로 변환

**세부 작업**:
- PyMuPDF4LLM 라이브러리 설치
- PDF → Markdown 변환 함수 구현
  ```python
  def extract_with_pymupdf(pdf_path: str) -> str:
      md_text = pymupdf4llm.to_markdown(pdf_path)
      return md_text
  ```
- 표 감지 및 파싱 로직 추가
- 이미지 추출 및 메타데이터 저장
- 페이지별 청킹 옵션 적용
- 오류 처리 및 로깅

**완료 기준**:
- PDF 파일을 Markdown으로 성공적으로 변환
- 표와 이미지가 올바르게 추출됨
- 샘플 PDF 테스트 통과

**예상 소요 시간**: 4일

---

#### Task 2.2: GPT-4 Vision 통합 (Path 2)
**목표**: PDF를 이미지로 변환하고 GPT-4 Vision으로 텍스트 추출

**세부 작업**:
- pdf2image 라이브러리 설치 및 설정
- PDF → 고해상도 이미지 변환 (DPI 300)
  ```python
  images = convert_from_path(pdf_path, dpi=300)
  ```
- 이미지 전처리 (그레이스케일, 노이즈 제거, 기울기 보정)
- OpenAI GPT-4 Vision API 통합
  ```python
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
  ```
- 배치 처리 및 병렬 실행 최적화
- API 호출 오류 처리 및 재시도 로직

**완료 기준**:
- PDF가 이미지로 변환됨
- GPT-4 Vision이 텍스트를 정확하게 추출
- 샘플 PDF 테스트 통과

**예상 소요 시간**: 5일

---

#### Task 2.3: 하이브리드 병합 로직 구현
**목표**: Path 1과 Path 2의 결과를 병합하여 최적의 텍스트 생성

**세부 작업**:
- 유사도 기반 중복 감지 (SequenceMatcher 사용)
  ```python
  similarity = SequenceMatcher(None, path1_result, path2_result).ratio()
  ```
- 신뢰도 점수 계산 및 최적 결과 선택
- 페이지별 콘텐츠 정렬 및 병합
- 품질 검증 로직
  - 완전성 검사 (블록 수 대비 점수)
  - 일관성 검사 (중복 여부)
  - 정확도 추정 (신뢰도 평균)
- 최종 Markdown 파일 생성 및 저장

**완료 기준**:
- Path 1과 Path 2 결과가 성공적으로 병합됨
- 품질 점수가 계산되고 기록됨
- 병합된 Markdown 파일이 생성됨

**예상 소요 시간**: 4일

---

#### Task 2.4: 청킹 및 임베딩 파이프라인
**목표**: Markdown 텍스트를 청크로 나누고 임베딩 생성

**세부 작업**:
- Fixed-size Chunking 구현
  - Chunk size: 1,000 토큰
  - Overlap: 50-100 토큰
  ```python
  def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
      chunks = []
      start = 0
      while start < len(text):
          end = start + chunk_size
          chunk = text[start:end]
          chunks.append(chunk)
          start = end - overlap
      return chunks
  ```
- 특수 청킹 처리
  - 표: 전체 표 단위로 하나의 chunk
  - 이미지: 설명 + 주변 텍스트 (200-400 토큰)
- OpenAI text-embedding-3-large 통합
  ```python
  response = client.embeddings.create(
      model="text-embedding-3-large",
      input=texts
  )
  ```
- 메타데이터 생성 (페이지 번호, 섹션, 타입 등)
- 토큰 카운팅 및 최적화

**완료 기준**:
- 텍스트가 청크로 성공적으로 분할됨
- 각 청크의 임베딩이 생성됨 (1536 차원)
- 메타데이터가 정확히 저장됨

**예상 소요 시간**: 3일

---

#### Task 2.5: 벡터 DB 저장
**목표**: 청크와 임베딩을 PostgreSQL에 저장

**세부 작업**:
- DocumentChunks 테이블에 데이터 삽입
  ```python
  async with session.begin():
      for chunk in chunks:
          db_chunk = DocumentChunk(
              document_id=doc_id,
              chunk_index=idx,
              chunk_type="text",
              content=chunk["text"],
              embedding=chunk["embedding"],
              metadata=chunk["metadata"]
          )
          session.add(db_chunk)
  ```
- 배치 삽입 최적화
- 중복 방지 (content_hash 사용)
- processing_logs 테이블에 처리 로그 기록
- 오류 발생 시 롤백 처리

**완료 기준**:
- 청크와 임베딩이 DB에 저장됨
- HNSW 인덱스가 자동 업데이트됨
- 처리 로그가 기록됨

**예상 소요 시간**: 2일

---

### Phase 3: LangGraph Multi-Agent 시스템 (3주)

#### Task 3.1: Router Agent 구현
**목표**: 사용자 요청을 분석하고 적절한 Agent로 라우팅

**세부 작업**:
- LangGraph StateGraph 초기화
- ISPLState 정의 (MessagesState 상속)
  ```python
  class ISPLState(MessagesState):
      next_agent: str
      task_type: str  # 'upload', 'search', 'manage'
      task_results: dict
  ```
- 의도 분류 로직 구현
  - 키워드 매칭 (업로드, 검색, 관리 등)
  - LLM 기반 의도 분류 (선택사항)
- Command 객체를 사용한 라우팅
  ```python
  return Command(
      goto=next_agent,
      update={"next_agent": next_agent}
  )
  ```
- 테스트 케이스 작성

**완료 기준**:
- Router Agent가 의도를 정확히 분류
- 적절한 Agent로 라우팅됨
- 단위 테스트 통과

**예상 소요 시간**: 3일

---

#### Task 3.2: Processing Agent 구현
**목표**: PDF 전처리 워크플로우를 실행하는 Agent

**세부 작업**:
- Processing Agent 노드 구현
- PDF 업로드 핸들러
- 하이브리드 전처리 파이프라인 호출
  - Path 1 (PyMuPDF4LLM)
  - Path 2 (GPT-4 Vision)
  - 병합 로직
- 진행 상태 업데이트 (processing_logs)
- 완료 후 Router로 복귀
- 오류 처리 및 재시도 로직

**완료 기준**:
- Processing Agent가 PDF를 성공적으로 처리
- 처리 결과가 DB에 저장됨
- 사용자에게 결과 메시지 전송

**예상 소요 시간**: 4일

---

#### Task 3.3: Search Agent 구현
**목표**: 하이브리드 벡터 검색을 수행하는 Agent

**세부 작업**:
- Search Agent 노드 구현
- 사용자 질의 전처리
  - 맞춤법 검사 (py-hanspell)
  - 전문용어 표준화
  - 동의어 확장
- 쿼리 임베딩 생성
- 하이브리드 검색 실행
  - 벡터 유사도 검색 (코사인)
  - 키워드 검색 (조항 번호 등)
  - 결과 융합 및 재순위화
- 유사도 임계값 필터링 (0.7 이상)
- 컨텍스트 최적화 (최대 8000 토큰)
- search_logs 테이블에 로그 기록

**완료 기준**:
- Search Agent가 관련 청크를 정확히 검색
- 유사도 점수가 계산됨
- 검색 로그가 기록됨

**예상 소요 시간**: 4일

---

#### Task 3.4: Answer Agent 구현
**목표**: LLM 기반 답변 생성 및 할루시네이션 방지

**세부 작업**:
- Answer Agent 노드 구현
- 시스템 프롬프트 설계
  ```
  당신은 보험약관 전문 상담사입니다. 다음 규칙을 반드시 준수하세요:
  1. 정확성 보장: 제공된 약관 내용에만 기반하여 답변하세요.
  2. 근거 제시: 모든 답변에 해당 약관 조항을 인용하세요.
  3. 한계 인정: 제공된 자료에 없는 내용은 "해당 정보가 약관에 명시되어 있지 않습니다"라고 답하세요.
  ```
- 컨텍스트 + 질의 조립
- GPT-4 API 호출 (temperature: 0.1)
- 할루시네이션 검증
  - 응답에 조항 번호 포함 확인
  - 원본 컨텍스트와 재대조
  - 신뢰도 점수 계산
- 응답 구조화 (답변, 소스 목록, 면책 조항)

**완료 기준**:
- Answer Agent가 정확한 답변 생성
- 조항 번호가 인용됨
- 할루시네이션이 최소화됨

**예상 소요 시간**: 4일

---

#### Task 3.5: Management Agent 구현
**목표**: 약관 목록 조회, 삭제, 다운로드 기능

**세부 작업**:
- Management Agent 노드 구현
- 약관 목록 조회
  - 필터링 (문서 타입, 상태, 기간 등)
  - 정렬 (업로드 날짜, 파일명 등)
  - 페이지네이션
- 약관 삭제
  - DB에서 documents 및 관련 chunks 삭제 (CASCADE)
  - 로컬 파일 삭제 (PDF, Markdown)
- 약관 다운로드
  - 원본 PDF 파일 제공
  - Markdown 파일 제공
- 권한 확인 (사용자별)

**완료 기준**:
- Management Agent가 CRUD 작업 수행
- 파일과 DB가 동기화됨
- 권한 검증이 동작함

**예상 소요 시간**: 3일

---

#### Task 3.6: Agent 간 통합 및 테스트
**목표**: 모든 Agent를 통합하고 End-to-End 테스트

**세부 작업**:
- StateGraph에 모든 Agent 추가
- Edge 연결 (START, END 포함)
- Command 기반 라우팅 검증
- 전체 워크플로우 테스트
  - 시나리오 1: PDF 업로드 → 전처리 → 저장
  - 시나리오 2: 질의 → 검색 → 답변
  - 시나리오 3: 약관 관리 (조회, 삭제)
- 오류 시나리오 테스트
- 성능 측정 및 최적화

**완료 기준**:
- 모든 Agent가 통합되어 동작
- 워크플로우가 원활히 실행됨
- 테스트 케이스 통과

**예상 소요 시간**: 4일

---

### Phase 4: 검색 및 답변 시스템 (2주)

#### Task 4.1: 하이브리드 검색 구현
**목표**: 벡터 검색과 키워드 검색을 결합한 고품질 검색 시스템

**세부 작업**:
- 벡터 유사도 검색 함수
- 키워드 검색 함수 (PostgreSQL Full-Text Search)
- 결과 융합 알고리즘
  - 가중치 기반 점수 계산
  - 중복 제거
  - 재순위화
- 필터링 옵션
  - 문서 타입
  - 시행 중인 약관만
  - 유사도 임계값 (0.7)
- 컨텍스트 최적화 (8000 토큰 제한)

**완료 기준**:
- 하이브리드 검색이 정확한 결과 반환
- 키워드와 벡터 검색이 적절히 결합됨
- 성능 테스트 통과

**예상 소요 시간**: 4일

---

#### Task 4.2: 할루시네이션 방지 프롬프트 설계
**목표**: LLM이 정확한 답변만 생성하도록 엄격한 프롬프트 설계

**세부 작업**:
- 시스템 프롬프트 정제
- 사용자 질의 프롬프트 템플릿 작성
- Few-shot 예제 추가 (선택사항)
- 응답 형식 강제 (JSON 스키마)
- 금지 사항 명시 (추측, 일반 상식 사용 금지)
- A/B 테스트로 프롬프트 최적화

**완료 기준**:
- 프롬프트가 할루시네이션을 최소화
- 조항 번호가 항상 인용됨
- 테스트 질의에서 높은 정확도

**예상 소요 시간**: 3일

---

#### Task 4.3: 답변 생성 및 검증 로직
**목표**: 생성된 답변을 검증하고 신뢰도를 평가

**세부 작업**:
- 답변 생성 함수
- 실시간 할루시네이션 검증
  - 조항 번호 존재 확인
  - 컨텍스트와 일치 여부 확인
  - 신뢰도 점수 계산
- 신뢰도 낮을 시 재생성 로직
- 응답 포맷팅
  - ①직접 답변
  - ②관련 약관 (조항 번호 포함)
  - ③주의사항
- 면책 조항 자동 추가

**완료 기준**:
- 답변 검증 로직이 동작
- 신뢰도 점수가 정확히 계산됨
- 답변이 일관된 형식으로 출력됨

**예상 소요 시간**: 4일

---

### Phase 5: Frontend 개발 (2주)

#### Task 5.1: 채팅 UI 구현
**목표**: GPT 스타일의 채팅 인터페이스 구축

**세부 작업**:
- ChatMessage 컴포넌트
  - 사용자 메시지
  - AI 답변 (Markdown 렌더링)
  - 참조 문서 표시
- ChatInput 컴포넌트
  - 텍스트 입력
  - 파일 업로드 버튼
  - 전송 버튼
- ChatHistory 컴포넌트 (좌측 사이드바)
  - 최근 대화 목록
  - 대화 선택 및 로드
- 실시간 스트리밍 응답 처리
  - Server-Sent Events (SSE) 또는 WebSocket
  - 타이핑 애니메이션
- 반응형 디자인 (모바일 지원)

**완료 기준**:
- 채팅 UI가 정상 동작
- 메시지 송수신이 원활
- 스트리밍 응답이 표시됨

**예상 소요 시간**: 5일

---

#### Task 5.2: 약관 관리 UI 구현
**목표**: 약관 업로드, 조회, 삭제 기능 UI

**세부 작업**:
- DocumentUpload 컴포넌트
  - 드래그 앤 드롭 업로드
  - 파일 선택 버튼
  - 업로드 진행률 표시
- DocumentList 컴포넌트
  - 약관 목록 테이블 뷰
  - 필터링 (문서 타입, 상태)
  - 정렬 (날짜, 이름)
  - 페이지네이션
- DocumentViewer 컴포넌트
  - PDF 뷰어 (react-pdf)
  - Markdown 뷰어
- 삭제 확인 다이얼로그
- 다운로드 버튼

**완료 기준**:
- 약관 관리 UI가 정상 동작
- 파일 업로드가 성공
- 목록 조회, 삭제, 다운로드가 동작

**예상 소요 시간**: 4일

---

#### Task 5.3: 참조 문서 패널 구현
**목표**: 답변에 사용된 약관 조항을 우측 패널에 표시

**세부 작업**:
- 참조 문서 패널 컴포넌트 (우측)
- 토글 기능 (열기/닫기)
- 참조된 청크 목록 표시
  - 문서명
  - 페이지 번호
  - 조항 번호
  - 유사도 점수
- 청크 클릭 시 상세 내용 표시
- 하이라이팅 기능

**완료 기준**:
- 참조 문서 패널이 정상 표시
- 클릭 시 상세 내용 표시
- 토글이 동작

**예상 소요 시간**: 2일

---

#### Task 5.4: API 통합
**목표**: Frontend와 Backend API 연결

**세부 작업**:
- API 클라이언트 설정 (axios 또는 fetch)
- API 엔드포인트 연결
  - POST /api/chat (채팅 메시지 전송)
  - GET /api/documents (약관 목록 조회)
  - POST /api/documents/upload (파일 업로드)
  - DELETE /api/documents/:id (약관 삭제)
  - GET /api/documents/:id/download (다운로드)
- 오류 처리 및 사용자 피드백
- 로딩 상태 표시
- 재시도 로직

**완료 기준**:
- 모든 API 엔드포인트가 연결됨
- 오류가 적절히 처리됨
- 사용자에게 피드백이 표시됨

**예상 소요 시간**: 3일

---

### Phase 6: 통합 및 테스트 (2주)

#### Task 6.1: Backend-Frontend 통합
**목표**: 전체 시스템 통합 및 동작 확인

**세부 작업**:
- CORS 설정 (FastAPI)
- 환경 변수 설정 (Frontend .env)
- 로컬 개발 환경 통합 테스트
- API 응답 형식 검증
- 오류 처리 일관성 확인

**완료 기준**:
- Frontend와 Backend가 원활히 통신
- 모든 기능이 정상 동작

**예상 소요 시간**: 3일

---

#### Task 6.2: End-to-End 테스트
**목표**: 전체 시나리오 기반 통합 테스트

**세부 작업**:
- 테스트 시나리오 작성
  1. PDF 업로드 → 전처리 → 저장 → 조회
  2. 약관 검색 → 답변 생성 → 참조 문서 표시
  3. 약관 관리 (삭제, 다운로드)
- 자동화 테스트 (Pytest + Playwright)
- 부하 테스트 (선택사항)
- 오류 시나리오 테스트
- 사용자 수용 테스트 (UAT)

**완료 기준**:
- 모든 시나리오 테스트 통과
- 주요 버그 수정 완료

**예상 소요 시간**: 4일

---

#### Task 6.3: 성능 최적화
**목표**: 시스템 성능 개선 및 병목 지점 제거

**세부 작업**:
- 데이터베이스 쿼리 최적화
- 임베딩 캐싱 (Redis)
- API 응답 시간 측정 및 개선
- HNSW 인덱스 파라미터 튜닝
- Frontend 번들 크기 최적화
- 이미지 및 리소스 최적화
- 메모리 사용량 모니터링

**완료 기준**:
- 평균 응답 시간 < 3초
- PDF 전처리 시간 최소화
- Frontend 로딩 시간 단축

**예상 소요 시간**: 3일

---

#### Task 6.4: 문서화
**목표**: 프로젝트 문서 작성 및 정리

**세부 작업**:
- README.md 업데이트
  - 프로젝트 개요
  - 설치 방법
  - 실행 방법
  - 환경 변수 설명
- API 문서 작성 (FastAPI 자동 생성 활용)
- 아키텍처 다이어그램 작성
- 데이터베이스 스키마 문서
- 배포 가이드 (선택사항)
- 트러블슈팅 가이드

**완료 기준**:
- 모든 문서가 작성되고 최신 상태
- 새로운 개발자가 문서만으로 프로젝트 이해 가능

**예상 소요 시간**: 4일

---

## 마일스톤 요약

| Phase | 기간 | 주요 산출물 |
|-------|-----|-----------|
| Phase 1: 기본 인프라 | 2주 | 프로젝트 구조, DB 설정, FastAPI 기본, Next.js 초기화 |
| Phase 2: PDF 전처리 | 3주 | PyMuPDF4LLM, GPT-4 Vision, 청킹, 임베딩, 벡터 저장 |
| Phase 3: Multi-Agent | 3주 | Router, Processing, Search, Answer, Management Agent |
| Phase 4: 검색/답변 | 2주 | 하이브리드 검색, 할루시네이션 방지, 답변 검증 |
| Phase 5: Frontend | 2주 | 채팅 UI, 약관 관리 UI, API 통합 |
| Phase 6: 통합/테스트 | 2주 | E2E 테스트, 성능 최적화, 문서화 |

**총 기간**: 14주 (약 3.5개월)

---

## 우선순위 및 리스크 관리

### 핵심 우선순위 (P0)
1. PDF 하이브리드 전처리 품질
2. 할루시네이션 방지
3. 벡터 검색 정확도
4. 사용자 경험 (UI/UX)

### 기술적 리스크
- **PDF 전처리 품질**: 샘플 PDF로 사전 검증, 하이브리드 방식으로 보완
- **LLM 할루시네이션**: 엄격한 프롬프트, 실시간 검증
- **API 비용**: 캐싱 전략, 배치 처리
- **성능 병목**: 비동기 처리, 인덱스 최적화

---

## 다음 단계

1. **Phase 1부터 순차적으로 시작**
2. **매 Phase 종료 시 검토 회의**
3. **주요 마일스톤마다 데모**
4. **지속적인 문서 업데이트**

이제 작업을 시작할 준비가 완료되었습니다! 🚀

