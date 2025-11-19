# 쿼리 전처리 개선: 조항 번호 추출 및 필터링

## 문제점

**벡터 검색의 한계**:
```
질의: "제15조의 내용이 무엇인가요?"
      ↓ (임베딩)
[0.23, -0.41, 0.18, ..., 0.56]  <- 1536차원 벡터
      ↓ (코사인 유사도 계산)
❌ "제15조"라는 정확한 키워드가 희석됨
❌ 일반적인 질문 패턴으로 임베딩되어 정확도 저하
```

## 해결 방법

### 1. 쿼리 전처리: 조항 번호 추출

**구현 위치**: `backend/agents/search_agent.py`

```python
def extract_clause_number(self, query: str) -> Optional[str]:
    """
    쿼리에서 조항 번호를 추출합니다.
    
    패턴:
    - "제15조" → "제15조"
    - "제 15 조" → "제15조"
    - "15조" → "제15조"
    """
    patterns = [
        r'제\s*(\d+)\s*조',  # 제15조, 제 15 조
        r'(\d+)\s*조',       # 15조
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            clause_num = match.group(1)
            return f"제{clause_num}조"
    
    return None
```

### 2. 메타데이터 필터링

**구현 위치**: `backend/services/vector_search.py`

SQL 쿼리에 조항 번호 필터 추가:

```sql
SELECT ...
FROM document_chunks c
INNER JOIN documents d ON c.document_id = d.id
WHERE 1 - (c.embedding <=> :query_embedding) > :threshold
    AND d.status = 'active'
    AND c.clause_number = :clause_number  -- ⭐ 추가된 필터
ORDER BY c.embedding <=> :query_embedding
LIMIT :limit
```

### 3. 통합 흐름

```
사용자 질의: "제15조의 내용이 무엇인가요?"
       ↓
[SearchAgent: extract_clause_number]
       ↓
조항 번호 추출: "제15조"
       ↓
threshold 조정: 0.7 → 0.3  ⭐ 추가!
(조항 번호로 필터링하므로 유사도 기준을 낮춤)
       ↓
[VectorSearchService]
       ↓
WHERE similarity > 0.3  ⬅️ 낮춤!
  AND clause_number = '제15조'  ⭐ 추가
       ↓
✅ "제15조"를 포함한 청크만 반환
```

**왜 threshold를 낮추나요?**
- **조항 번호 없음**: threshold=0.7 (높은 유사도 필요)
  - 예: "암 진단비는?" → 다양한 청크 중 유사도 높은 것만
  
- **조항 번호 있음**: threshold=0.3 (낮은 유사도 허용)
  - 예: "제15조의 내용?" → 이미 조항 번호로 필터링됨
  - 유사도가 낮아도 "제15조" 청크는 모두 관련 있음
  - AND 조건으로 인한 결과 누락 방지!

## 수정된 파일

### 1. `backend/agents/search_agent.py`
- ✅ `extract_clause_number()` 메서드 추가
- ✅ `search()` 메서드에서 조항 번호 추출 및 전달

### 2. `backend/services/vector_search.py`
- ✅ `search()` 메서드에 `clause_number` 파라미터 추가
- ✅ `_search_vectors()` 메서드에 필터링 로직 추가
- ✅ SQL 쿼리에 `clause_filter` 조건 추가

## 테스트 케이스

### Before (조항 번호 필터 없음)
```
질의: "제15조의 내용이 무엇인가요?"
결과: 다양한 조항들이 섞여서 반환 (제3조, 제7조, 제15조 등)
유사도: 0.65, 0.68, 0.71, ...
❌ 제15조가 상위권에 안 올 수 있음
```

### After (조항 번호 필터 적용)
```
질의: "제15조의 내용이 무엇인가요?"
      ↓ 조항 번호 추출: "제15조"
결과: "제15조"를 포함한 청크만 반환
유사도: 0.71, 0.68, 0.65, ...
✅ 모두 제15조 관련 내용
```

## 효과

### 1. 정확도 향상
- **Before**: 조항 번호 질의 시 다른 조항이 섞임
- **After**: 정확히 해당 조항만 반환

### 2. 사용자 경험 개선
- 조항 번호를 명시한 질의에 대한 즉각적인 정확한 답변
- 불필요한 다른 조항 정보 제거

### 3. 로그 가시성
```
INFO - 쿼리에서 조항 번호 추출: 제15조
INFO - 📋 조항 번호 필터 적용: 제15조
INFO - 조항 번호 필터 적용: 제15조
```

## 한계 및 향후 개선

### 현재 구현의 한계
1. **단일 조항만 지원**: "제3조와 제5조"와 같은 복수 조항 미지원
2. **벡터 검색 의존**: 조항 번호만 있어도 벡터 검색을 수행 (비효율)
3. **키워드 검색 부재**: 순수 키워드 매칭 없음

### Phase 2.1.1: 하이브리드 검색 (예정)
```python
# 조항 번호가 있으면 키워드 검색 우선
if clause_number:
    # 1. 키워드 검색 (빠름, 정확)
    keyword_results = keyword_search(clause_number)
    
    # 2. 벡터 검색 (의미적 확장)
    vector_results = vector_search(query, clause_filter)
    
    # 3. 결과 융합
    final_results = merge_results(keyword_results, vector_results)
```

### 추가 개선 사항
1. **조항 항 번호 지원**: "제3조 제2항"
2. **복수 조항 지원**: "제3조와 제5조", "제3조~제5조"
3. **동의어 확장**: "3조" = "제3조" = "제 삼 조"
4. **쿼리 보정**: "15조" → "제15조"로 자동 보정

## 검증 방법

### 1. 단위 테스트
```bash
cd d:\APP\ispl3\backend
python -c "
from agents.search_agent import SearchAgent
agent = SearchAgent()
print(agent.extract_clause_number('제15조의 내용이 무엇인가요?'))  # 제15조
print(agent.extract_clause_number('15조 알려줘'))  # 제15조
print(agent.extract_clause_number('암 진단비는?'))  # None
"
```

### 2. 통합 테스트
```bash
cd d:\APP\ispl3\backend
python test\test_hallucination_prevention.py
```

테스트 케이스 "구체적 질의 - 조항 번호 포함"에서:
- 질의: "제15조의 내용이 무엇인가요?"
- 로그에서 "조항 번호 필터 적용: 제15조" 확인
- 검색 결과가 모두 제15조 관련인지 확인

## 결론

✅ **즉시 적용 가능한 개선**으로 조항 번호 질의의 정확도를 크게 향상시킴

✅ **벡터 검색 + 메타데이터 필터링** 조합으로 최상의 결과 제공

✅ **Phase 2.1.1 하이브리드 검색**의 기반이 되는 중요한 첫걸음

🚀 **다음 단계**: Phase 2.1.1에서 키워드 검색과 완전히 통합하여 더욱 강력한 하이브리드 검색 구현

