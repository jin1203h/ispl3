# ISPL 프로젝트 - 기능 중심 작업 계획 (v2)

**작성일**: 2025년 10월 14일  
**프로젝트명**: ISPL (Insurance Policy) - Agentic AI System  
**접근 방식**: End-to-End 기능 중심 수직 슬라이싱  
**총 예상 기간**: 12주 (약 3개월)

---

## 🎯 계획 원칙

1. **수직 슬라이싱**: 각 Sprint는 Frontend부터 Backend까지 완전한 기능 제공
2. **빠른 검증**: 매 Sprint마다 동작하는 시스템 산출
3. **병렬 개발**: Frontend와 Backend 팀이 동시 작업 가능
4. **점진적 확장**: MVP부터 시작하여 기능 추가

---

## Phase 1: MVP - 기본 인프라 + PDF 검색 시스템 (4주)

### Sprint 1.1: 기본 인프라 구축 (1주)

#### 목표
Backend 및 Frontend 기본 구조를 구축하고 데이터베이스를 설정하여 개발 준비 완료

#### Backend Tasks
- **Task 1.1.1**: 프로젝트 구조 및 환경 설정 (1일)
  - Python 가상환경 생성
  - FastAPI 프로젝트 초기화
  - 디렉토리 구조 생성 (agents/, api/, models/, services/)
  - requirements.txt 작성
  - 환경 변수 설정 (.env.example)

- **Task 1.1.2**: PostgreSQL + pgvector 설정 (2일)
  - PostgreSQL 17.6 설치 및 데이터베이스 생성
  - pgvector extension 설치
  - schema.sql 작성 (users, documents, document_chunks, processing_logs, search_logs)
  - HNSW 인덱스 생성

- **Task 1.1.3**: FastAPI 기본 구조 및 DB 연결 (2일)
  - SQLAlchemy 비동기 엔진 설정
  - 의존성 주입 패턴 구현 (SessionDep)
  - ORM 모델 정의 (Documents, DocumentChunks)
  - Pydantic 스키마 정의
  - 헬스체크 엔드포인트 (`/health`)

#### Frontend Tasks
- **Task 1.1.4**: Next.js 프로젝트 초기화 (2일)
  - Next.js 15 + TypeScript 프로젝트 생성
  - Tailwind CSS 설정
  - 기본 레이아웃 컴포넌트 (Header, Sidebar)
  - 라우팅 구조 (`/`, `/documents`)
  - API 클라이언트 설정 (axios)

#### 완료 기준
- ✅ PostgreSQL + pgvector가 정상 동작
- ✅ FastAPI 서버가 실행되고 `/health` 응답
- ✅ Next.js 개발 서버가 실행되고 기본 레이아웃 렌더링
- ✅ Frontend → Backend API 통신 확인

#### 예상 소요 시간: 5일

---

### Sprint 1.2: PDF 자동 처리 파이프라인 (1.5주)

#### 목표
PDF 업로드부터 벡터 DB 저장까지 완전한 자동 처리 파이프라인 구현

#### Backend Tasks
- **Task 1.2.1**: PyMuPDF4LLM 통합 (Path 1) (2일)
  - PyMuPDF4LLM 설치 및 PDF → Markdown 변환 함수
  - 표 감지 및 파싱
  - 이미지 추출 및 메타데이터 저장
  - 페이지별 구조화
  - 오류 처리 및 로깅

- **Task 1.2.2**: GPT-4 Vision 통합 (Path 2) (2일)
  - pdf2image로 고해상도 이미지 변환 (DPI 300)
  - 이미지 전처리 (그레이스케일, 노이즈 제거)
  - OpenAI GPT-4 Vision API 통합
  - 배치 처리 및 병렬 실행
  - 오류 처리 및 재시도 로직

- **Task 1.2.3**: 하이브리드 병합 및 품질 검증 (1.5일)
  - 유사도 기반 중복 감지 (SequenceMatcher)
  - 신뢰도 점수 계산 및 최적 결과 선택
  - 품질 검증 로직 (완전성, 일관성, 정확도)
  - 최종 Markdown 파일 생성 및 저장

- **Task 1.2.4**: 청킹 및 임베딩 (2일)
  - Fixed-size Chunking (1,000 토큰, overlap 100)
  - 특수 청킹 (표, 이미지)
  - OpenAI text-embedding-3-large 통합
  - 메타데이터 생성
  - 벡터 DB 저장 (배치 삽입)

#### Frontend Tasks
- **Task 1.2.5**: PDF 업로드 UI (1.5일)
  - DocumentUpload 컴포넌트 (드래그 앤 드롭)
  - 파일 선택 및 검증
  - 업로드 진행률 표시
  - 처리 상태 실시간 업데이트

#### API 설계
- `POST /api/documents/upload` - PDF 업로드
- `GET /api/documents/{id}/status` - 처리 상태 조회

#### 완료 기준
- ✅ PDF 파일 업로드 → 자동 전처리 → 벡터 DB 저장
- ✅ 하이브리드 방식으로 고품질 텍스트 추출
- ✅ Frontend에서 업로드 및 진행 상황 확인 가능
- ✅ 샘플 보험약관 PDF 테스트 성공

#### 예상 소요 시간: 7일

---

### Sprint 1.3: 기본 벡터 검색 시스템 (1.5주)

#### 목표
사용자 질의에 대한 벡터 검색 및 기본 답변 생성

#### Backend Tasks
- **Task 1.3.1**: 벡터 검색 엔진 (2일)
  - 쿼리 임베딩 생성
  - pgvector 코사인 유사도 검색
  - 유사도 임계값 필터링 (0.7 이상)
  - 검색 결과 정렬 및 반환
  - search_logs 테이블에 로그 기록

- **Task 1.3.2**: 기본 LangGraph Agent 구조 (3일)
  - LangGraph StateGraph 초기화
  - ISPLState 정의
  - Router Agent (의도 분류: search/upload/manage)
  - Search Agent (벡터 검색 수행)
  - Answer Agent (GPT-4 기반 답변 생성)
  - Agent 간 라우팅 (Command 패턴)

- **Task 1.3.3**: 할루시네이션 방지 프롬프트 (1.5일)
  - 시스템 프롬프트 설계 (정확성 보장, 근거 제시, 한계 인정)
  - 조항 번호 강제 인용
  - 응답 구조화 (답변, 관련 약관, 주의사항)

#### Frontend Tasks
- **Task 1.3.4**: 검색 UI 및 채팅 인터페이스 (2일)
  - ChatInput 컴포넌트 (텍스트 입력, 전송)
  - ChatMessage 컴포넌트 (사용자/AI 메시지)
  - Markdown 렌더링
  - 로딩 상태 표시

#### API 설계
- `POST /api/chat` - 채팅 메시지 전송 및 답변 수신

#### 완료 기준
- ✅ 사용자 질의 → 벡터 검색 → AI 답변 생성
- ✅ 답변에 조항 번호 포함
- ✅ 채팅 UI에서 검색 및 답변 확인 가능
- ✅ 기본적인 할루시네이션 방지

#### 예상 소요 시간: 7일

---

## Phase 2: 검색 품질 향상 + 약관 관리 (3주)

### Sprint 2.1: 하이브리드 검색 및 답변 검증 (1주)

#### 목표
벡터 검색과 키워드 검색을 결합하고, 답변 품질 검증 강화

#### Backend Tasks
- **Task 2.1.1**: 하이브리드 검색 구현 (2일)
  - PostgreSQL Full-Text Search (키워드 검색)
  - 벡터 검색과 키워드 검색 결과 융합
  - 가중치 기반 재순위화
  - 컨텍스트 최적화 (8000 토큰 제한)

- **Task 2.1.2**: 질의 전처리 (1.5일)
  - 맞춤법 검사 (py-hanspell)
  - 전문용어 표준화 (term_dictionary)
  - 동의어 확장
  - 불완전 질의 감지

- **Task 2.1.3**: 답변 검증 로직 (1.5일)
  - 실시간 할루시네이션 검증
  - 조항 번호 존재 확인
  - 컨텍스트와 일치 여부 확인
  - 신뢰도 점수 계산
  - 신뢰도 낮을 시 재생성

#### Frontend Tasks
- **Task 2.1.4**: 참조 문서 패널 (1일)
  - 우측 패널 컴포넌트
  - 참조된 청크 목록 표시 (문서명, 페이지, 조항, 유사도)
  - 청크 클릭 시 상세 내용
  - 토글 기능

#### 완료 기준
- ✅ 하이브리드 검색으로 더 정확한 결과
- ✅ 답변 검증 및 신뢰도 점수 표시
- ✅ 참조 문서 패널에서 출처 확인 가능

#### 예상 소요 시간: 5일

---

### Sprint 2.2: 약관 관리 기능 (1주)

#### 목표
약관 목록 조회, 삭제, 다운로드 기능 구현

#### Backend Tasks
- **Task 2.2.1**: Management Agent 구현 (2일)
  - 약관 목록 조회 (필터링, 정렬, 페이지네이션)
  - 약관 삭제 (DB + 로컬 파일)
  - 약관 다운로드 (PDF, Markdown)
  - 권한 확인

- **Task 2.2.2**: Management API 엔드포인트 (1일)
  - `GET /api/documents` - 목록 조회
  - `DELETE /api/documents/{id}` - 삭제
  - `GET /api/documents/{id}/download` - 다운로드
  - `GET /api/documents/{id}/view` - PDF/Markdown 조회

#### Frontend Tasks
- **Task 2.2.3**: 약관 관리 UI (2일)
  - DocumentList 컴포넌트 (테이블 뷰)
  - 필터링 및 정렬 UI
  - 페이지네이션
  - 삭제 확인 다이얼로그
  - 다운로드 버튼
  - DocumentViewer (PDF/Markdown 뷰어)

#### 완료 기준
- ✅ 약관 목록 조회 및 필터링
- ✅ 약관 삭제 기능
- ✅ PDF 및 Markdown 다운로드
- ✅ PDF/Markdown 뷰어

#### 예상 소요 시간: 5일

---

### Sprint 2.3: Processing Agent 및 자동화 (1주)

#### 목표
PDF 업로드부터 검색 가능까지 완전 자동화

#### Backend Tasks
- **Task 2.3.1**: Processing Agent 구현 (2일)
  - Processing Agent 노드
  - PDF 업로드 핸들러
  - 하이브리드 전처리 파이프라인 호출
  - 진행 상태 업데이트 (processing_logs)
  - 완료 후 Router로 복귀
  - 오류 처리 및 재시도 로직

- **Task 2.3.2**: 자동화 워크플로우 (2일)
  - Router Agent 강화 (upload 의도 분류)
  - Processing Agent → Router → 완료 메시지
  - 백그라운드 작업 처리 (Celery 또는 asyncio)
  - 진행 상황 실시간 업데이트 (WebSocket)

#### Frontend Tasks
- **Task 2.3.3**: 실시간 진행 상황 UI (1일)
  - WebSocket 또는 SSE 연결
  - 진행률 바 및 단계별 상태
  - 완료/오류 알림

#### 완료 기준
- ✅ PDF 업로드 시 자동으로 전처리 및 검색 가능
- ✅ 진행 상황 실시간 표시
- ✅ 완료 알림

#### 예상 소요 시간: 5일

---

## Phase 3: UX 향상 + 성능 최적화 (3주)

### Sprint 3.1: 채팅 UI 고도화 (1주)

#### 목표
GPT 스타일의 완성도 높은 채팅 인터페이스

#### Frontend Tasks
- **Task 3.1.1**: 스트리밍 응답 처리 (2일)
  - Server-Sent Events (SSE) 구현
  - 타이핑 애니메이션
  - 스트리밍 중 취소 기능

- **Task 3.1.2**: 대화 이력 관리 (2일)
  - ChatHistory 컴포넌트 (좌측 사이드바)
  - 대화 목록 (최근순)
  - 대화 선택 및 로드
  - 대화 삭제 및 이름 변경

- **Task 3.1.3**: 반응형 디자인 (1일)
  - 모바일 레이아웃
  - 사이드바 토글
  - 터치 제스처 지원

#### Backend Tasks
- **Task 3.1.4**: 대화 세션 관리 (1일)
  - 대화 저장 및 로드
  - 대화 컨텍스트 유지
  - 세션 관리

#### 완료 기준
- ✅ 스트리밍 응답으로 실시간 답변 표시
- ✅ 대화 이력 저장 및 관리
- ✅ 모바일에서도 사용 가능

#### 예상 소요 시간: 5일

---

### Sprint 3.2: 성능 최적화 (1주)

#### 목표
시스템 응답 속도 개선 및 비용 절감

#### Backend Tasks
- **Task 3.2.1**: 캐싱 전략 (2일)
  - Redis 설치 및 설정 (로컬 Redis 서비스)
  - 임베딩 캐싱 (동일 청크)
  - 검색 결과 캐싱 (동일 쿼리)
  - LLM 응답 캐싱 (선택사항)

- **Task 3.2.2**: 데이터베이스 최적화 (1.5일)
  - 쿼리 최적화 (EXPLAIN ANALYZE)
  - 인덱스 튜닝
  - Connection Pooling 설정
  - HNSW 파라미터 튜닝 (m, ef_construction)

- **Task 3.2.3**: API 성능 개선 (1.5일)
  - 배치 처리 최적화
  - 비동기 처리 강화
  - 응답 압축 (gzip)
  - API 응답 시간 모니터링

#### Frontend Tasks
- **Task 3.2.4**: Frontend 최적화 (1일)
  - 번들 크기 최적화
  - 코드 스플리팅
  - 이미지 최적화
  - 레이지 로딩

#### 완료 기준
- ✅ 평균 응답 시간 < 3초
- ✅ PDF 전처리 시간 단축
- ✅ Frontend 초기 로딩 < 2초

#### 예상 소요 시간: 5일

---

### Sprint 3.3: 테스트 및 문서화 (1주)

#### 목표
전체 시스템 테스트 및 문서 정비

#### Tasks
- **Task 3.3.1**: End-to-End 테스트 (2일)
  - 테스트 시나리오 작성
    1. PDF 업로드 → 전처리 → 검색
    2. 약관 검색 → 답변 생성 → 참조 문서 확인
    3. 약관 관리 (조회, 삭제, 다운로드)
  - 자동화 테스트 (Pytest + Playwright)
  - 오류 시나리오 테스트

- **Task 3.3.2**: 단위 테스트 보강 (1일)
  - Agent 단위 테스트
  - API 엔드포인트 테스트
  - 컴포넌트 테스트 (React Testing Library)

- **Task 3.3.3**: 문서화 (2일)
  - README.md 업데이트 (설치, 실행, 환경 변수)
  - API 문서 (FastAPI 자동 생성)
  - 아키텍처 다이어그램
  - 데이터베이스 스키마 문서
  - 사용자 가이드
  - 트러블슈팅 가이드

#### 완료 기준
- ✅ 모든 E2E 테스트 통과
- ✅ 테스트 커버리지 > 70%
- ✅ 완전한 문서화

#### 예상 소요 시간: 5일

---

## Phase 4: 고급 기능 (2주, 선택사항)

### Sprint 4.1: 고급 검색 기능 (1주)

#### Tasks
- **Task 4.1.1**: 고급 필터링
  - 문서 타입별 검색
  - 날짜 범위 검색
  - 보험사별 검색
  - 특정 조항 검색

- **Task 4.1.2**: 검색 결과 하이라이팅
  - 매칭 키워드 강조
  - 중요 문장 표시

- **Task 4.1.3**: 검색 히스토리
  - 최근 검색어
  - 인기 검색어
  - 검색어 자동완성

#### 예상 소요 시간: 5일

---

### Sprint 4.2: 사용자 관리 및 권한 (1주)

#### Tasks
- **Task 4.2.1**: 사용자 인증
  - 회원가입 / 로그인
  - JWT 토큰 관리
  - 비밀번호 암호화

- **Task 4.2.2**: 권한 관리
  - 역할 기반 접근 제어 (RBAC)
  - 관리자 / 일반 사용자
  - 약관 업로드 권한

- **Task 4.2.3**: 사용자 프로필
  - 프로필 조회 및 수정
  - 관심 보험 유형 설정
  - 검색 이력 조회

#### 예상 소요 시간: 5일

---

## 📊 전체 로드맵

| Phase | Sprint | 기간 | 주요 산출물 | 누적 기간 |
|-------|--------|-----|-----------|---------|
| **Phase 1: MVP** | Sprint 1.1 | 1주 | 기본 인프라 | 1주 |
| | Sprint 1.2 | 1.5주 | PDF 자동 처리 | 2.5주 |
| | Sprint 1.3 | 1.5주 | 기본 검색 + 답변 | 4주 |
| **Phase 2: 고도화** | Sprint 2.1 | 1주 | 하이브리드 검색 | 5주 |
| | Sprint 2.2 | 1주 | 약관 관리 | 6주 |
| | Sprint 2.3 | 1주 | Processing Agent | 7주 |
| **Phase 3: 최적화** | Sprint 3.1 | 1주 | 채팅 UI 고도화 | 8주 |
| | Sprint 3.2 | 1주 | 성능 최적화 | 9주 |
| | Sprint 3.3 | 1주 | 테스트 + 문서화 | 10주 |
| **Phase 4: 선택** | Sprint 4.1 | 1주 | 고급 검색 | 11주 |
| | Sprint 4.2 | 1주 | 사용자 관리 | 12주 |

**총 기간**: 10주 (필수) + 2주 (선택) = **10-12주**

---

## 🎯 핵심 개선 사항

### 기존 계획과 비교

| 항목 | 기존 (v1) | 개선 (v2) |
|-----|----------|----------|
| **첫 데모** | 10주 후 | 4주 후 |
| **병렬 개발** | 불가능 | 가능 |
| **검증 주기** | 14주 | 매 1-2주 |
| **총 기간** | 14주 | 10주 (필수) |
| **접근 방식** | 기술 계층별 | 기능 단위별 |
| **리스크** | 후반 집중 | 전체 분산 |

### 주요 장점

1. **빠른 가치 제공**: 4주 만에 동작하는 검색 시스템
2. **병렬 개발**: Frontend/Backend 팀이 동시 작업
3. **빠른 피드백**: 매 Sprint마다 사용자 테스트 가능
4. **리스크 분산**: 초기부터 통합 테스트
5. **팀 사기**: 빠른 성과로 동기 부여

---

## 📌 Sprint별 우선순위

### P0 (필수)
- Phase 1 전체 (Sprint 1.1 ~ 1.3)
- Phase 2 전체 (Sprint 2.1 ~ 2.3)
- Phase 3: Sprint 3.3 (테스트 + 문서화)

### P1 (중요)
- Phase 3: Sprint 3.1 (채팅 UI 고도화)
- Phase 3: Sprint 3.2 (성능 최적화)

### P2 (선택)
- Phase 4 전체 (고급 기능)

---

## 🚀 시작 가이드

### 1단계: Sprint 1.1부터 시작
```bash
# Backend 설정
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# PostgreSQL + pgvector 설정
python scripts/init_db.py

# Frontend 설정
cd frontend
npm install
npm run dev
```

### 2단계: 매 Sprint 종료 시
- 데모 및 회고
- 다음 Sprint 계획 조정
- 우선순위 재검토

### 3단계: Phase 1 완료 후
- 사용자 피드백 수집
- Phase 2 세부 계획 확정
- 필요시 우선순위 변경

---

## 💡 성공 기준

### Phase 1 완료 시 (4주)
- ✅ PDF 업로드 가능
- ✅ 자동 전처리 및 벡터 저장
- ✅ 약관 검색 및 AI 답변
- ✅ 기본 채팅 UI

### Phase 2 완료 시 (7주)
- ✅ 고품질 하이브리드 검색
- ✅ 약관 관리 기능
- ✅ 완전 자동화된 워크플로우

### Phase 3 완료 시 (10주)
- ✅ 완성도 높은 UI/UX
- ✅ 응답 시간 < 3초
- ✅ 완전한 테스트 및 문서화
- ✅ **배포 가능한 시스템**

---

이제 작업을 시작할 준비가 완료되었습니다! 🚀

