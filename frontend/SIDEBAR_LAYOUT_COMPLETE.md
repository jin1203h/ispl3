# 사이드바 레이아웃 및 약관관리 화면 구현 ✅

## 완료 날짜
2025-10-16

## 구현 내용

### 1. 사이드바 컴포넌트 ✅

**파일**: `frontend/components/Sidebar.tsx`

#### 기능
- 로고/헤더 영역
- 메뉴 네비게이션
  - 💬 AI 채팅 (`/chat`)
  - 📋 최근 대화 (`/history`)
  - 📄 약관 관리 (`/documents`)
- 현재 페이지 하이라이트
- 하단 버전 정보

#### 스타일
- 고정 너비: 256px (w-64)
- 다크 테마 (bg-gray-900)
- 선택된 메뉴: 파란색 배경 (bg-blue-600)
- 호버 효과: bg-gray-800

---

### 2. 공통 레이아웃 컴포넌트 ✅

**파일**: `frontend/components/AppLayout.tsx`

#### 구조
```
┌────────┬─────────────────────────┐
│        │                         │
│ Side   │   Main Content          │
│ bar    │   (children)            │
│        │                         │
└────────┴─────────────────────────┘
```

- Flexbox 레이아웃
- 사이드바: 고정
- 콘텐츠: flex-1, 스크롤 가능

---

### 3. 업로드 모달 컴포넌트 ✅

**파일**: `frontend/components/UploadModal.tsx`

#### 기능
- 파일 선택 (PDF만)
- 추출 방법 선택
  - PyMuPDF (빠름, 일반 문서)
  - Vision API (느림, 표/이미지)
  - 하이브리드 (가장 정확, 가장 느림)
- 진행률 표시
- 오류 처리
- 모달 닫기 (업로드 중 비활성화)

#### Props
```typescript
interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}
```

---

### 4. 약관 관리 페이지 ✅

**파일**: `frontend/app/documents/page.tsx`

#### 기능

**상단**
- 헤더: "약관 관리"
- 업로드 버튼: 클릭 시 모달 오픈

**콘텐츠**
1. **등록된 약관 목록**
   - 카드 형식 (그리드 레이아웃)
   - 파일명, 회사명, 상태
   - 페이지 수, 청크 수
   - 등록일
   - 삭제 버튼

2. **빈 상태**
   - 안내 메시지
   - 업로드 버튼

3. **로딩 상태**
   - 스피너 애니메이션

4. **오류 상태**
   - 오류 메시지 표시

#### API 통합
- `GET /api/documents`: 문서 목록 조회
- `DELETE /api/documents/{id}`: 문서 삭제

---

### 5. 최근 대화 페이지 ✅

**파일**: `frontend/app/history/page.tsx`

#### 내용
- Phase 2 개발 예정 안내
- 예정 기능 소개
  - 대화 이력 자동 저장
  - 날짜별 그룹화
  - 대화 검색
  - 대화 내보내기

---

### 6. 채팅 페이지 수정 ✅

**파일**: `frontend/app/chat/page.tsx`

#### 변경사항
- `AppLayout` 컴포넌트로 감싸기
- 전체 화면 헤더 → 컨텐츠 영역 헤더로 변경
- 기존 기능 유지

---

### 7. 백엔드 문서 관리 API ✅

**파일**: `backend/api/documents.py`

#### 엔드포인트

**1. GET /api/documents**
- 문서 목록 조회
- 각 문서의 청크 수 포함
- 최신순 정렬

**2. GET /api/documents/{id}**
- 문서 상세 조회
- 메타데이터 포함

**3. DELETE /api/documents/{id}**
- 문서 삭제 (Soft delete)
- status를 'deleted'로 변경

#### 응답 예시

**목록 조회**
```json
{
  "documents": [
    {
      "id": 1,
      "filename": "sample_policy.pdf",
      "document_type": "policy",
      "company_name": "ABC보험",
      "status": "active",
      "created_at": "2025-10-16T10:00:00",
      "total_pages": 25,
      "total_chunks": 123
    }
  ],
  "total": 1
}
```

---

## 화면 구성

### 전체 레이아웃

```
┌─────────────┬──────────────────────────────────┐
│             │                                  │
│  🏥 ISPL    │  [페이지 제목]                    │
│  보험약관    │                                  │
│  AI 시스템   │                                  │
│             │                                  │
├─────────────┤                                  │
│             │                                  │
│ 💬 AI 채팅  │                                  │
│   보험약관   │        콘텐츠 영역                │
│   질문하기   │                                  │
│             │                                  │
│ 📋 최근대화  │                                  │
│   대화이력   │                                  │
│   보기       │                                  │
│             │                                  │
│ 📄 약관관리  │                                  │
│   약관업로드 │                                  │
│   및 관리    │                                  │
│             │                                  │
├─────────────┤                                  │
│ v1.0.0      │                                  │
│ © 2025 ISPL │                                  │
└─────────────┴──────────────────────────────────┘
```

### 약관 관리 화면

```
┌──────────────────────────────────────────────┐
│ 약관 관리                    [📄 약관 업로드] │
│ 등록된 보험약관을 관리합니다                   │
├──────────────────────────────────────────────┤
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ sample_  │  │ policy_  │  │ terms_   │ │
│  │ policy_  │  │ abc.pdf  │  │ xyz.pdf  │ │
│  │ 1.pdf    │  │          │  │          │ │
│  │          │  │ ABC보험   │  │ XYZ보험   │ │
│  │ 활성      │  │ 활성      │  │ 활성      │ │
│  │          │  │          │  │          │ │
│  │ 25페이지  │  │ 30페이지  │  │ 15페이지  │ │
│  │ 123청크   │  │ 150청크   │  │ 80청크    │ │
│  │          │  │          │  │          │ │
│  │ 2025-10- │  │ 2025-10- │  │ 2025-10- │ │
│  │ 15       │  │ 14       │  │ 13       │ │
│  │          │  │          │  │          │ │
│  │ [삭제]    │  │ [삭제]    │  │ [삭제]    │ │
│  └──────────┘  └──────────┘  └──────────┘ │
│                                              │
└──────────────────────────────────────────────┘
```

### 업로드 모달

```
┌───────────────────────────────────────┐
│ 약관 업로드                        ✕ │
├───────────────────────────────────────┤
│                                       │
│ PDF 파일                              │
│ ┌───────────────────────────────────┐│
│ │ [파일 선택]  선택된 파일 없음      ││
│ └───────────────────────────────────┘│
│                                       │
│ 추출 방법                             │
│ ○ PyMuPDF (빠름, 일반 문서)           │
│ ○ Vision API (느림, 표/이미지)        │
│ ○ 하이브리드 (가장 정확, 가장 느림)   │
│                                       │
│                         [취소] [업로드]│
└───────────────────────────────────────┘
```

---

## 파일 구조

```
frontend/
├── app/
│   ├── chat/
│   │   └── page.tsx              (수정)
│   ├── documents/
│   │   └── page.tsx              (수정 - 약관관리)
│   ├── history/
│   │   └── page.tsx              (신규 - 최근대화)
│   └── page.tsx                  (기존)
└── components/
    ├── AppLayout.tsx             (신규)
    ├── Sidebar.tsx               (신규)
    ├── UploadModal.tsx           (신규)
    ├── ChatInput.tsx             (기존)
    ├── ChatMessage.tsx           (기존)
    └── DocumentUpload.tsx        (기존)

backend/
└── api/
    └── documents.py              (신규)
```

---

## 주요 개선사항

### Before (기존)
- 각 페이지가 독립적
- 네비게이션 없음
- 업로드 페이지 전체 화면

### After (개선)
✅ **통일된 레이아웃**
- 모든 페이지에 사이드바
- 일관된 사용자 경험

✅ **편리한 네비게이션**
- 언제든지 메뉴 이동 가능
- 현재 페이지 시각적 표시

✅ **모달 방식 업로드**
- 팝업으로 업로드
- 페이지 이동 없음
- 업로드 후 자동 새로고침

✅ **약관 목록 관리**
- 카드 형식으로 보기 쉬움
- 즉시 삭제 가능
- 통계 정보 표시

---

## 테스트 방법

### 1. 서버 실행

**백엔드**
```bash
cd backend
python main.py
```

**프론트엔드**
```bash
cd frontend
npm install  # 처음 한 번만
npm run dev
```

### 2. 테스트 시나리오

#### 시나리오 1: 사이드바 네비게이션
1. http://localhost:3000/chat 접속
2. 사이드바에서 "약관 관리" 클릭
3. 사이드바에서 "최근 대화" 클릭
4. 사이드바에서 "AI 채팅" 클릭
5. 확인: 선택된 메뉴 파란색 하이라이트

#### 시나리오 2: 약관 업로드
1. "약관 관리" 페이지로 이동
2. "약관 업로드" 버튼 클릭
3. 모달에서 PDF 파일 선택
4. 추출 방법 선택
5. "업로드" 버튼 클릭
6. 진행률 확인
7. 업로드 완료 후 목록에 표시되는지 확인

#### 시나리오 3: 약관 목록
1. "약관 관리" 페이지에서 카드 확인
   - 파일명
   - 회사명
   - 페이지 수
   - 청크 수
   - 등록일
   - 상태 (활성/비활성)

#### 시나리오 4: 약관 삭제
1. 카드의 "삭제" 버튼 클릭
2. 확인 다이얼로그 확인
3. "확인" 클릭
4. 목록에서 제거되는지 확인

#### 시나리오 5: 빈 상태
1. 모든 문서 삭제
2. 빈 상태 메시지 확인
3. "약관 업로드" 버튼 확인

---

## API 명세

### GET /api/documents
문서 목록 조회

**Response**
```json
{
  "documents": [
    {
      "id": 1,
      "filename": "sample_policy.pdf",
      "document_type": "policy",
      "company_name": "ABC보험",
      "status": "active",
      "created_at": "2025-10-16T10:00:00",
      "total_pages": 25,
      "total_chunks": 123
    }
  ],
  "total": 1
}
```

### GET /api/documents/{id}
문서 상세 조회

**Response**
```json
{
  "id": 1,
  "filename": "sample_policy.pdf",
  "document_type": "policy",
  "company_name": "ABC보험",
  "status": "active",
  "created_at": "2025-10-16T10:00:00",
  "updated_at": "2025-10-16T10:00:00",
  "total_pages": 25,
  "file_size": 1024000,
  "pdf_path": "uploads/documents/sample_policy.pdf",
  "markdown_path": "uploads/documents/sample_policy.md",
  "metadata": {},
  "total_chunks": 123
}
```

### DELETE /api/documents/{id}
문서 삭제 (Soft delete)

**Response**
```json
{
  "message": "문서가 삭제되었습니다",
  "document_id": 1,
  "filename": "sample_policy.pdf"
}
```

---

## 향후 개선 사항

### Phase 2 예정
1. **최근 대화 기능**
   - 대화 이력 저장
   - 날짜별 그룹화
   - 대화 검색
   - 대화 내보내기

2. **문서 상세 보기**
   - 청크 목록 표시
   - 페이지별 미리보기

3. **문서 필터링**
   - 회사별 필터
   - 상태별 필터
   - 날짜 범위 필터

4. **대량 업로드**
   - 여러 파일 동시 업로드
   - 진행률 개별 표시

5. **문서 편집**
   - 메타데이터 수정
   - 상태 변경 (활성/비활성)

---

## 알려진 이슈

### 해결 완료
- ✅ 사이드바 레이아웃
- ✅ 모달 팝업
- ✅ 약관 목록 조회
- ✅ 약관 삭제

### 추후 개선 필요
- ⚠️ 대량 데이터 페이지네이션
- ⚠️ 업로드 취소 기능
- ⚠️ 문서 검색 기능

---

## 결론

✅ **사이드바 레이아웃 구현 완료**
- 통일된 네비게이션
- 일관된 사용자 경험

✅ **약관 관리 화면 구현 완료**
- 목록 조회
- 모달 업로드
- 문서 삭제

🚀 **다음 단계**: Phase 2 기능 추가 (최근 대화, 문서 상세 등)

---

## 생성/수정된 파일

### 신규 생성
- `frontend/components/Sidebar.tsx`
- `frontend/components/AppLayout.tsx`
- `frontend/components/UploadModal.tsx`
- `frontend/app/history/page.tsx`
- `backend/api/documents.py`
- `frontend/SIDEBAR_LAYOUT_COMPLETE.md` (이 문서)

### 수정
- `frontend/app/chat/page.tsx`
- `frontend/app/documents/page.tsx`
- `backend/main.py`

