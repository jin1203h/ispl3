# ISPL - 보험약관 기반 Agentic AI 시스템

Insurance Policy AI System - LangGraph Multi-Agent 기반 보험약관 검색 및 답변 시스템

## 프로젝트 개요

보험약관 PDF를 업로드하여 AI 시스템에 등록하고, 자연어 질문에 대해 정확한 답변을 제공하는 시스템입니다.

### 주요 기능
- 📄 **PDF 업로드 및 전처리**: 하이브리드 방식(직접 추출 + GPT-4 Vision)으로 PDF 처리
- 🔍 **벡터 검색**: pgvector 기반 의미론적 검색
- 🤖 **Multi-Agent 시스템**: LangGraph 기반 Router, Processing, Search, Answer, Management Agent
- 💬 **채팅 인터페이스**: GPT 스타일의 대화형 UI
- 📊 **약관 관리**: 업로드된 약관 목록 조회, 삭제, 다운로드

## 기술 스택

### Backend
- **FastAPI**: 비동기 웹 프레임워크
- **PostgreSQL 17.6 + pgvector**: 벡터 데이터베이스
- **LangGraph**: Multi-Agent 워크플로우
- **OpenAI**: GPT-4, text-embedding-3-large
- **PyMuPDF4LLM**: PDF 텍스트 추출
- **SQLAlchemy**: ORM

### Frontend
- **Next.js 15**: React 프레임워크
- **TypeScript**: 타입 안정성
- **Tailwind CSS**: 스타일링

## 설치 및 실행

### 사전 요구사항
- Python 3.11+
- Node.js 18+
- PostgreSQL 17.6
- OpenAI API Key

### 1. 데이터베이스 설정

```bash
# PostgreSQL 설치 및 실행
# pgvector extension 설치

# 데이터베이스 생성
createdb ispl

# 스키마 초기화
psql -d ispl -f backend/schema.sql
```

### 2. Backend 설정

```bash
cd backend

# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (Linux/Mac)
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
# .env 파일 생성 후 다음 내용 추가:
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ispl
# OPENAI_API_KEY=your_openai_api_key

# 서버 실행
python main.py
```

Backend 서버는 http://localhost:8000 에서 실행됩니다.

### 3. Frontend 설정

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

Frontend 서버는 http://localhost:3000 에서 실행됩니다.

## API 문서

Backend 서버 실행 후 http://localhost:8000/docs 에서 Swagger UI를 통해 API 문서를 확인할 수 있습니다.

## 프로젝트 구조

```
ispl/
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph Agent 구현
│   │   ├── api/             # FastAPI 라우터
│   │   ├── core/            # 설정, 데이터베이스
│   │   ├── models/          # SQLAlchemy 모델
│   │   └── services/        # 비즈니스 로직
│   ├── main.py              # 서버 실행 스크립트
│   ├── requirements.txt     # Python 의존성
│   └── schema.sql           # 데이터베이스 스키마
├── frontend/
│   ├── app/                 # Next.js 페이지
│   ├── components/          # React 컴포넌트
│   └── lib/                 # 유틸리티
├── uploads/                 # 업로드된 파일 저장
└── doc/                     # 문서
```

## 개발 가이드

### Backend 개발
- FastAPI 비동기 패턴 사용
- SQLAlchemy ORM으로 데이터베이스 접근
- LangGraph로 Agent 워크플로우 구성
- 모든 코드와 주석은 한글로 작성

### Frontend 개발
- Server Component 우선 사용
- Client Component는 'use client' 명시
- Tailwind CSS로 스타일링
- TypeScript 엄격 모드 사용

## 라이선스

MIT License

## 참고 문서
- [PRD](doc/Insurance%20Policy_prd.md)
- [Architecture](doc/architecture/README.md)
- [Task Plan](doc/ISPL_Task_Plan_v2.md)

