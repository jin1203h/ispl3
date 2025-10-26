# PDF 업로드 UI - Sprint 1.2.5

## 구현 내용

### 1. API 클라이언트 (`lib/api.ts`)
- Backend API와 통신하기 위한 유틸리티
- `uploadPDF()`: PDF 파일 업로드 함수
- `checkHealth()`: Health 체크 함수
- TypeScript 타입 정의 포함

### 2. DocumentUpload 컴포넌트 (`components/DocumentUpload.tsx`)
- **드래그 앤 드롭**: 파일을 드래그하여 업로드 가능
- **파일 검증**: PDF만 허용, 50MB 제한
- **업로드 진행률**: 0%~100% 진행률 표시
- **처리 옵션**: 
  - PyMuPDF (빠름)
  - GPT-4 Vision (정확, 비용 발생)
  - 하이브리드 (가장 정확, 비용 발생)
- **청킹 옵션**: 검색 기능 활성화 여부 선택
- **상태 표시**: 업로드 중, 성공, 오류 메시지

### 3. 문서 관리 페이지 (`app/documents/page.tsx`)
- PDF 업로드 UI
- 업로드된 문서 목록 표시
- 청킹 정보 및 품질 평가 결과 표시

## 사용 방법

### 1. 환경 변수 설정

`frontend/.env.local` 파일을 생성하고 다음 내용을 추가:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. 개발 서버 실행

```bash
cd frontend
npm install  # 최초 1회만
npm run dev
```

### 3. 브라우저에서 접속

- 홈페이지: http://localhost:3000
- 문서 업로드: http://localhost:3000/documents

## 기능 테스트

### 1. 드래그 앤 드롭 테스트
1. `/documents` 페이지 접속
2. PDF 파일을 드래그하여 업로드 영역에 드롭
3. 파일 정보 확인

### 2. 파일 선택 테스트
1. "파일 선택" 클릭
2. PDF 파일 선택
3. 파일 정보 확인

### 3. 파일 검증 테스트
1. PDF가 아닌 파일 선택 → 오류 메시지 표시
2. 50MB 이상 파일 선택 → 오류 메시지 표시

### 4. 업로드 테스트
1. PDF 파일 선택
2. 처리 방법 선택 (PyMuPDF 권장)
3. "청킹 및 임베딩 활성화" 체크
4. "업로드 시작" 클릭
5. 진행률 0%~100% 확인
6. 성공 메시지 및 업로드된 문서 정보 확인

## 주요 기능

### ✅ 구현 완료
- [x] 드래그 앤 드롭 파일 선택
- [x] 파일 형식 검증 (PDF만)
- [x] 파일 크기 검증 (최대 50MB)
- [x] 업로드 진행률 표시
- [x] 처리 방법 선택 (pymupdf/vision/both)
- [x] 청킹 및 임베딩 옵션
- [x] 성공/오류 메시지 표시
- [x] 업로드된 문서 목록
- [x] 청킹 정보 표시
- [x] 품질 평가 결과 표시

## API 엔드포인트

### POST /api/pdf/upload
- **파일**: PDF 파일
- **method**: `pymupdf` | `vision` | `both`
- **enable_chunking**: `true` | `false`

**응답**:
```json
{
  "message": "PDF 처리 완료",
  "document_id": 123,
  "filename": "sample.pdf",
  "metadata": {
    "total_pages": 10,
    "quality": {
      "overall_score": 0.95,
      "status": "excellent"
    }
  },
  "chunks": {
    "total_chunks": 15,
    "saved_to_db": true
  }
}
```

## 기술 스택

- **Frontend**: Next.js 15, React 18, TypeScript
- **Styling**: Tailwind CSS
- **API**: Fetch API (native)
- **State Management**: React useState

## 참고사항

- 업로드 진행률은 시뮬레이션입니다 (실제 파일 업로드 진행률 추적은 복잡함)
- Backend 서버(`http://localhost:8000`)가 실행 중이어야 합니다
- CORS가 올바르게 설정되어 있어야 합니다

