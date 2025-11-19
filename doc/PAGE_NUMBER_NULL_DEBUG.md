# page_number가 NULL이 되는 원인 분석

## 🚨 문제: 3가지 방식 모두 `page_number`가 NULL

### 🔍 가능한 원인

#### 1. **`pages_info`가 비어있거나 전달되지 않음**
```python
# _chunk_and_embed() 호출 시
if pages_info:  # ← 이게 False면 실행 안됨
    chunks = self._assign_vision_page_numbers(...)
```

**확인 방법:**
- `result.get('pages', [])` 값이 빈 리스트일 수 있음
- PyMuPDF, Vision API, Hybrid 각각 `pages` 반환 여부 확인 필요

---

#### 2. **Markdown에 "## 페이지 X" 패턴이 없음**
```python
pattern = f"## 페이지 {vision_page_num}"
pos = markdown_text.find(pattern)
if pos >= 0:  # ← 못 찾으면 page_positions가 비어있음
    page_positions.append(...)
```

**가능한 상황:**
- PyMuPDF: `extract_full_document()`에서 페이지 마커 추가가 안됨
- Vision API: `extract_full_document()`에서 페이지 마커 추가가 안됨
- Hybrid: `extract_with_context()`에서 페이지 마커 추가가 안됨

---

#### 3. **청크 내용을 Markdown에서 찾지 못함**
```python
search_content = chunk.content[:100]
chunk_pos = markdown_text.find(search_content)

if chunk_pos < 0:  # ← 못 찾으면 NULL
    logger.warning(f"청크 위치를 찾을 수 없음")
    continue
```

**원인:**
- 청킹 시 내용이 변형됨 (공백, 줄바꿈 정규화 등)
- Markdown 텍스트와 청크 텍스트가 일치하지 않음

---

#### 4. **`page_positions`가 비어있음**
```python
for page_info in reversed(page_positions):  # ← 빈 리스트면 실행 안됨
    if page_info['position'] <= chunk_pos:
        current_page = page_info['vision_page_number']
        break

# current_page가 None으로 남음
chunk.page_number = current_page  # ← NULL!
```

---

## 🔧 해결 방법

### 1단계: 디버깅 로그 강화

```python
def _assign_vision_page_numbers(
    self,
    chunks: List,
    markdown_text: str,
    pages_info: List[Dict]
) -> List:
    """각 청크에 Vision의 page_number를 할당합니다."""
    
    # 🔍 디버깅 1: 입력값 확인
    logger.info(f"=== page_number 할당 시작 ===")
    logger.info(f"청크 수: {len(chunks)}")
    logger.info(f"pages_info 수: {len(pages_info)}")
    logger.info(f"Markdown 길이: {len(markdown_text)}")
    logger.info(f"Markdown 앞부분 200자: {markdown_text[:200]}")
    
    # Markdown에서 "## 페이지 X" 위치 찾기
    page_positions = []
    for page_info in pages_info:
        vision_page_num = page_info['page_number']
        pattern = f"## 페이지 {vision_page_num}"
        pos = markdown_text.find(pattern)
        
        # 🔍 디버깅 2: 패턴 검색 결과
        logger.info(f"패턴 '{pattern}' 검색: pos={pos}")
        
        if pos >= 0:
            page_positions.append({
                'vision_page_number': vision_page_num,
                'position': pos
            })
        else:
            logger.warning(f"⚠️ 패턴 '{pattern}'을 찾을 수 없음!")
    
    # 위치 기준 정렬
    page_positions.sort(key=lambda x: x['position'])
    
    # 🔍 디버깅 3: 페이지 위치 확인
    logger.info(f"감지된 페이지 위치: {len(page_positions)}개")
    for pp in page_positions[:3]:  # 처음 3개만 로그
        logger.info(f"  - 페이지 {pp['vision_page_number']}: position {pp['position']}")
    
    if not page_positions:
        logger.error("❌ 페이지 위치를 하나도 찾지 못했습니다!")
        logger.error(f"Markdown 시작 부분 확인: {markdown_text[:500]}")
        return chunks
    
    # 각 청크가 어느 Vision 페이지에 속하는지 판단
    success_count = 0
    fail_count = 0
    
    for chunk in chunks:
        # 청크의 위치 찾기
        search_content = chunk.content[:100] if len(chunk.content) > 100 else chunk.content
        chunk_pos = markdown_text.find(search_content)
        
        if chunk_pos < 0:
            # 🔍 디버깅 4: 청크 찾기 실패
            logger.warning(
                f"⚠️ 청크 {chunk.chunk_index} 위치를 찾을 수 없음. "
                f"내용 앞 50자: {chunk.content[:50]}"
            )
            fail_count += 1
            continue
        
        # 청크보다 앞에 있는 가장 가까운 페이지 찾기
        current_page = None
        for page_info in reversed(page_positions):
            if page_info['position'] <= chunk_pos:
                current_page = page_info['vision_page_number']
                break
        
        # 할당
        chunk.page_number = current_page
        
        if current_page:
            success_count += 1
            logger.debug(f"✅ Chunk {chunk.chunk_index} → Page {current_page}")
        else:
            # 🔍 디버깅 5: 페이지 할당 실패
            logger.warning(
                f"⚠️ 청크 {chunk.chunk_index}의 페이지를 찾을 수 없음. "
                f"chunk_pos={chunk_pos}, 첫 페이지 위치={page_positions[0]['position']}"
            )
            fail_count += 1
    
    # 🔍 디버깅 6: 최종 통계
    logger.info(f"=== page_number 할당 완료 ===")
    logger.info(f"✅ 성공: {success_count}개")
    logger.info(f"❌ 실패: {fail_count}개")
    logger.info(f"📊 성공률: {success_count}/{len(chunks)} ({success_count*100/len(chunks):.1f}%)")
    
    return chunks
```

---

### 2단계: Vision API의 `extract_full_document()` 확인

Vision API가 `pages` 정보를 반환하는지 확인:

```python
# backend/services/vision_extractor.py
async def extract_full_document(
    self,
    pdf_path: str,
    apply_preprocessing: bool = True
) -> Dict:
    # ...
    
    # 4. 결과 병합
    pages = []  # ← 이게 비어있을 수 있음!
    total_tokens = 0
    
    for result in sorted(results, key=lambda x: x['page_number']):
        pages.append({
            'page_number': result['page_number'],
            'content': result['content']
        })
        total_tokens += result['tokens_used']['total']
    
    # 🔍 디버깅: pages 확인
    logger.info(f"pages 생성: {len(pages)}개")
    
    # Markdown으로 병합
    markdown_parts = []
    for page in pages:
        markdown_parts.append(f"## 페이지 {page['page_number']}\n")
        markdown_parts.append(page['content'])
        markdown_parts.append("\n---\n")
    
    full_markdown = "\n".join(markdown_parts)
    
    # 🔍 디버깅: Markdown 확인
    logger.info(f"Markdown 길이: {len(full_markdown)}")
    logger.info(f"Markdown 앞부분: {full_markdown[:200]}")
    
    return {
        'markdown': full_markdown,
        'pages': pages,  # ← 이게 반환되는지 확인!
        'metadata': {...}
    }
```

---

### 3단계: PyMuPDF의 `extract_full_document()` 확인

PyMuPDF가 페이지 마커를 추가하는지 확인:

```python
# backend/services/pymupdf_extractor.py
def extract_full_document(self, pdf_path: str, ...) -> Dict:
    # 1. 페이지별 데이터 추출
    pages = self.extract_by_pages(pdf_path)
    
    # 🔍 디버깅: pages 확인
    logger.info(f"PyMuPDF pages: {len(pages)}개")
    
    # 2. 페이지별 Markdown을 "## 페이지 X" 마커와 함께 결합
    markdown_parts = []
    for page in pages:
        page_num = page['page_number']
        page_content = page['content'].strip()
        
        # 페이지 마커 추가
        markdown_parts.append(f"## 페이지 {page_num}\n\n{page_content}")
    
    full_markdown = "\n\n".join(markdown_parts)
    
    # 🔍 디버깅: Markdown 확인
    logger.info(f"PyMuPDF Markdown 길이: {len(full_markdown)}")
    logger.info(f"PyMuPDF Markdown 앞부분: {full_markdown[:200]}")
    
    return {
        'markdown': full_markdown,
        'pages': pages,  # ← 이게 반환되는지 확인!
        'metadata': {...}
    }
```

---

## 🎯 가장 가능성 높은 원인

### **원인 1: Vision API의 `extract_full_document()`에 `pages` 없음**

```python
# backend/services/vision_extractor.py (라인 325-368)
async def extract_full_document(
    self,
    pdf_path: str,
    apply_preprocessing: bool = True
) -> Dict:
    # ...
    return {
        'markdown': full_markdown,
        # 'pages': pages,  # ← 이게 빠져있을 수 있음!
        'metadata': {...}
    }
```

### **원인 2: `_process_with_vision_async()`에서 `pages` 전달 안함**

```python
# backend/services/pdf_processor.py (라인 133-136)
async def _process_with_vision_async(self, pdf_path: str) -> Dict:
    logger.info("Path 2: GPT-4 Vision 처리")
    return await self.vision_extractor.extract_full_document(pdf_path)
    # ← 이게 pages를 반환하지 않으면 NULL 발생
```

---

## ✅ 최종 해결 방안

1. **Vision API `extract_full_document()` 확인**
   - `pages` 리스트가 반환되는지 확인
   - 없으면 추가

2. **디버깅 로그 추가**
   - `_assign_vision_page_numbers()` 전체에 상세 로그 추가
   - 어느 단계에서 실패하는지 확인

3. **로그 확인 후 원인 파악**
   - "페이지 위치를 하나도 찾지 못했습니다" → Markdown에 "## 페이지 X" 없음
   - "청크 위치를 찾을 수 없음" → 청킹 시 텍스트 변형
   - "청크의 페이지를 찾을 수 없음" → 첫 페이지보다 앞에 청크가 있음

코드를 수정하시겠습니까?

