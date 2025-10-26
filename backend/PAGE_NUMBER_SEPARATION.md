# 페이지 번호 분리 변경사항

## 📅 변경 일자
2025-10-21

## 🎯 변경 목표
- **DB의 `page_number`**: Vision의 물리적 순서 (1, 2, 3...)
- **DB의 `pdf_page_number`**: PDF 내부 인쇄 페이지 번호 (3, 5, 7... 또는 NULL)
- **청킹 방식**: 전체 Markdown을 한번에 청킹 후, 각 청크가 어느 Vision 페이지에 속하는지 판단
- **Markdown 형식 통일**: PyMuPDF와 Vision API 모두 `## 페이지 X` 형식 사용

---

## 🔧 수정된 파일

### 1. 데이터베이스 스키마 (`backend/database/schema.sql`)

#### 변경 내용
```sql
CREATE TABLE IF NOT EXISTS document_chunks (
    -- ...
    page_number INTEGER, -- Vision의 물리적 순서 (1, 2, 3...)
    pdf_page_number INTEGER, -- PDF 내부 인쇄 페이지 번호
    -- ...
);

CREATE INDEX IF NOT EXISTS idx_chunks_pdf_page ON document_chunks(pdf_page_number);
```

#### 설명
- `page_number`: Vision API가 처리한 페이지의 물리적 순서
- `pdf_page_number`: Markdown에서 추출한 PDF 내부 인쇄 번호 (예: "### 3" → 3)

---

### 2. ORM 모델 (`backend/models/document_chunk.py`)

#### 변경 내용
```python
class DocumentChunk(Base):
    # ...
    page_number = Column(Integer)  # Vision의 물리적 순서 (1, 2, 3...)
    pdf_page_number = Column(Integer)  # PDF 내부 인쇄 페이지 번호
    # ...
```

---

### 3. Chunk 데이터 클래스 (`backend/services/chunker.py`)

#### 변경 내용
```python
@dataclass
class Chunk:
    content: str
    chunk_index: int
    chunk_type: str
    page_number: int = None  # Vision의 물리적 순서 (나중에 할당)
    pdf_page_number: int = None  # PDF 내부 인쇄 페이지 번호 (Markdown에서 추출)
    # ...
```

#### 메타데이터 추출 로직 변경
```python
# 페이지 번호 추정 (### 숫자 패턴)
page_match = re.search(r'^###\s+(\d+)\s+', content, re.MULTILINE)

if page_match:
    chunk.pdf_page_number = int(page_match.group(1))  # ← 변경됨
```

**Before**: `chunk.page_number = ...`  
**After**: `chunk.pdf_page_number = ...`

---

### 4. PDF Processor (`backend/services/pdf_processor.py`)

#### A. Import 추가
```python
from typing import Dict, Optional, Literal, List  # List 추가
```

#### B. `process_pdf()` 수정
```python
# 청킹 및 임베딩
if enable_chunking:
    pages_info = result.get('pages', [])  # Vision의 pages 정보
    chunks_data = await self._chunk_and_embed(
        result['markdown'],
        document_id,
        db_session,
        pages_info=pages_info  # 추가
    )
```

#### C. `_chunk_and_embed()` 수정
```python
async def _chunk_and_embed(
    self,
    markdown_text: str,
    document_id: int,
    db_session = None,
    pages_info: List[Dict] = None  # 추가
) -> Dict:
    # 1. 텍스트 청킹
    chunks = self.chunker.chunk_markdown(...)
    
    # 2. Vision page_number 할당
    if pages_info:
        chunks = self._assign_vision_page_numbers(chunks, markdown_text, pages_info)
    
    # 3. 임베딩 생성
    # 4. DB 저장
    # 5. 결과 반환
```

#### D. 새 메서드 추가: `_assign_vision_page_numbers()`
```python
def _assign_vision_page_numbers(
    self,
    chunks: List,
    markdown_text: str,
    pages_info: List[Dict]
) -> List:
    """
    각 청크에 Vision의 page_number를 할당합니다.
    
    작동 방식:
    1. Markdown에서 "## 페이지 X" 위치 찾기
    2. 각 청크의 위치 찾기
    3. 청크보다 앞에 있는 가장 가까운 페이지 할당
    """
    # Markdown에서 "## 페이지 X" 위치 찾기
    page_positions = []
    for page_info in pages_info:
        vision_page_num = page_info['page_number']
        pattern = f"## 페이지 {vision_page_num}"
        pos = markdown_text.find(pattern)
        if pos >= 0:
            page_positions.append({
                'vision_page_number': vision_page_num,
                'position': pos
            })
    
    # 위치 기준 정렬
    page_positions.sort(key=lambda x: x['position'])
    
    # 각 청크가 어느 Vision 페이지에 속하는지 판단
    for chunk in chunks:
        search_content = chunk.content[:100] if len(chunk.content) > 100 else chunk.content
        chunk_pos = markdown_text.find(search_content)
        
        if chunk_pos < 0:
            continue
        
        # 청크보다 앞에 있는 가장 가까운 페이지 찾기
        current_page = None
        for page_info in reversed(page_positions):
            if page_info['position'] <= chunk_pos:
                current_page = page_info['vision_page_number']
                break
        
        chunk.page_number = current_page
    
    return chunks
```

---

### 5. Chunk Repository (`backend/services/chunk_repository.py`)

#### 변경 내용
```python
db_chunk = DocumentChunk(
    document_id=document_id,
    chunk_index=chunk.chunk_index,
    chunk_type=chunk.chunk_type,
    page_number=chunk.page_number,  # Vision의 물리적 순서
    pdf_page_number=chunk.pdf_page_number,  # PDF 내부 인쇄 페이지 번호
    # ...
)
```

**추가된 필드**: `pdf_page_number=chunk.pdf_page_number`

---

### 6. PyMuPDF Extractor (`backend/services/pymupdf_extractor.py`)

#### 변경 내용: Markdown 형식 통일
```python
def extract_full_document(self, pdf_path: str, ...) -> Dict:
    # 1. 페이지별 데이터 추출 (먼저 수행)
    pages = self.extract_by_pages(pdf_path)
    
    # 2. 페이지별 Markdown을 "## 페이지 X" 마커와 함께 결합
    markdown_parts = []
    for page in pages:
        page_num = page['page_number']
        page_content = page['content'].strip()
        
        # 페이지 마커 추가 (Vision API와 동일한 형식)
        markdown_parts.append(f"## 페이지 {page_num}\n\n{page_content}")
    
    # 전체 Markdown 생성
    full_markdown = "\n\n".join(markdown_parts)
    
    # 3. 표 감지
    # 4. 이미지 감지
    # 5. 메타데이터 생성
```

#### 설명
- **Before**: PyMuPDF는 페이지 구분선(`-----`) 사용
- **After**: Vision API와 동일한 `## 페이지 X` 형식 사용
- **효과**: `_assign_vision_page_numbers()`가 PyMuPDF 결과에도 적용 가능

---

### 7. Migration SQL (`backend/database/migrations/add_pdf_page_number.sql`)

```sql
-- 1. 컬럼 추가
ALTER TABLE document_chunks 
ADD COLUMN IF NOT EXISTS pdf_page_number INTEGER;

-- 2. 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_chunks_pdf_page ON document_chunks(pdf_page_number);

-- 3. 주석 추가
COMMENT ON COLUMN document_chunks.page_number IS 'Vision의 물리적 순서 (1, 2, 3...)';
COMMENT ON COLUMN document_chunks.pdf_page_number IS 'PDF 내부 인쇄 페이지 번호';
```

---

## 📊 작동 흐름

### PyMuPDF 처리
```
1. PyMuPDF 페이지별 추출
   pages = [
     {page_number: 1, content: "제1조..."},
     {page_number: 2, content: "제2조..."}
   ]

2. Markdown 생성 (마커 추가)
   ## 페이지 1    ← position 0
   
   제1조...
   ### 3
   
   ## 페이지 2    ← position 500
   
   제2조...
   ### 5

3. 청킹
   chunk1: content="### 3\n제1조...", pdf_page_number=3
   chunk2: content="### 5\n제2조...", pdf_page_number=5

4. page_number 할당
   page_positions = [
     {vision_page_number: 1, position: 0},
     {vision_page_number: 2, position: 500}
   ]
   
   chunk1.position = 10 → 가장 가까운 페이지는 1 → chunk1.page_number = 1
   chunk2.position = 510 → 가장 가까운 페이지는 2 → chunk2.page_number = 2

5. DB 저장
   chunk1: page_number=1, pdf_page_number=3
   chunk2: page_number=2, pdf_page_number=5
```

### Vision API 처리
```
1. Vision API 처리
   pages = [
     {page_number: 1, content: "..."},
     {page_number: 2, content: "..."}
   ]

2. Markdown 생성
   ## 페이지 1    ← position 0
   ### 3
   제1조...
   
   ## 페이지 2    ← position 500
   ### 5
   제2조...

3. 청킹
   chunk1: content="### 3\n제1조...", pdf_page_number=3
   chunk2: content="### 5\n제2조...", pdf_page_number=5

4. page_number 할당
   (동일한 로직)

5. DB 저장
   chunk1: page_number=1, pdf_page_number=3
   chunk2: page_number=2, pdf_page_number=5
```

### Hybrid 처리
```
1. PyMuPDF 텍스트 추출 → Vision API 컨텍스트로 제공
2. Vision API가 Markdown 생성 (## 페이지 X 형식)
3. Vision의 pages 정보 사용
4. 청킹 및 page_number 할당
5. DB 저장
```

---

## ✅ 최종 DB 결과 예시

| chunk_index | page_number | pdf_page_number | content |
|-------------|-------------|-----------------|---------|
| 0 | 1 | 3 | 제1조... |
| 1 | 2 | 5 | 제2조... |
| 2 | 2 | NULL | 표... |

---

## 🎯 세 가지 처리 방식 비교

| 항목 | PyMuPDF | Vision API | Hybrid (Both) |
|------|---------|------------|---------------|
| **Markdown 형식** | ✅ `## 페이지 X` | ✅ `## 페이지 X` | ✅ `## 페이지 X` |
| **pages 정보** | ✅ 있음 | ✅ 있음 | ✅ 있음 (Vision) |
| **page_number** | ✅ 할당됨 | ✅ 할당됨 | ✅ 할당됨 |
| **pdf_page_number** | ✅ 추출됨 | ✅ 추출됨 | ✅ 추출됨 |
| **물리적 순서** | 1, 2, 3... | 1, 2, 3... | 1, 2, 3... |
| **처리 속도** | 빠름 | 느림 | 중간 |
| **정확도** | 텍스트만 | 텍스트+이미지 | 최고 |

---

## 🚀 적용 방법

### 1. 기존 데이터베이스에 적용
```bash
psql -U your_user -d your_db -f backend/database/migrations/add_pdf_page_number.sql
```

### 2. 새로운 데이터베이스 생성
```bash
psql -U your_user -d your_db -f backend/database/schema.sql
```

---

## 🔍 검증 방법

### 1. PDF 업로드 후 DB 확인
```sql
SELECT 
    chunk_index,
    page_number,
    pdf_page_number,
    LEFT(content, 50) as content_preview
FROM document_chunks
WHERE document_id = <your_document_id>
ORDER BY chunk_index
LIMIT 10;
```

### 2. 예상 결과
- `page_number`: 1, 2, 3... (연속적)
- `pdf_page_number`: 3, 5, 7... (불연속 가능, NULL 가능)

### 3. Markdown 형식 확인
```python
# PyMuPDF 처리 결과
result = processor.process_pdf(pdf_path, method="pymupdf")
print(result['markdown'][:200])
# 출력: ## 페이지 1\n\n제1조...

# Vision API 처리 결과
result = processor.process_pdf(pdf_path, method="vision")
print(result['markdown'][:200])
# 출력: ## 페이지 1\n\n제1조...
```

---

## 📝 주의사항

1. **Markdown 형식 통일**
   - PyMuPDF와 Vision API 모두 `## 페이지 X` 형식 사용
   - `_assign_vision_page_numbers()`가 모든 처리 방식에 적용 가능

2. **기존 데이터 마이그레이션**
   - 기존 `page_number`를 `pdf_page_number`로 복사하려면:
     ```sql
     UPDATE document_chunks 
     SET pdf_page_number = page_number 
     WHERE pdf_page_number IS NULL;
     ```

3. **NULL 값 처리**
   - `page_number`: 페이지 마커를 찾지 못한 경우 NULL 가능
   - `pdf_page_number`: Markdown에서 번호 추출 실패 시 NULL

4. **성능 고려사항**
   - PyMuPDF: 페이지별 추출 후 결합 (약간의 오버헤드 추가)
   - Vision API: 변경 없음
   - Hybrid: 변경 없음

---

## 🎉 완료
이제 모든 처리 방식(PyMuPDF, Vision API, Hybrid)에서 일관된 방식으로 페이지 번호를 관리할 수 있습니다!

