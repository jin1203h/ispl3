# 하이브리드 방식 변경 사항

## 📋 개요

약관 업로드 시 하이브리드 방식(method="both")을 변경하여 PyMuPDF 텍스트를 Vision API의 입력 컨텍스트로 활용하도록 개선했습니다.

## 🔄 변경 사항

### **기존 방식**
```
1. PyMuPDF로 텍스트 추출 → 결과 A
2. Vision API로 이미지에서 텍스트 추출 → 결과 B
3. 결과 A와 B를 유사도 기반으로 병합
```

### **새로운 방식 (진정한 하이브리드)**
```
1. PyMuPDF로 텍스트 추출 (빠르고 정확)
2. PDF를 이미지로 변환
3. Vision API 호출 시:
   - 입력 1: 이미지 (base64)
   - 입력 2: PyMuPDF 추출 텍스트 (컨텍스트)
   → Vision API가 텍스트를 검증하고 표/이미지/레이아웃 정보를 보완
4. Vision API의 출력을 최종 결과로 사용
```

## ✨ 장점

1. **정확도 향상**: PyMuPDF의 빠른 텍스트 + Vision의 시각 정보 이해력 결합
2. **표 처리 개선**: 텍스트를 참고하여 표 구조를 더 정확하게 파악
3. **이미지 설명**: 텍스트 컨텍스트를 활용하여 이미지/도식을 더 정확하게 설명
4. **단일 출력**: 후처리 병합이 불필요하여 로직 단순화
5. **토큰 효율성**: Vision API가 텍스트를 미리 알고 있어 더 효율적

## 📝 수정된 파일

### 1. `backend/services/vision_extractor.py`
- `extract_text_from_image()`: `context_text` 파라미터 추가
  - 하이브리드 모드와 일반 모드를 구분하는 프롬프트 생성
  - 컨텍스트 텍스트가 있을 때 텍스트 검증 및 보완 지시
  
- `extract_batch()`: `context_texts` 파라미터 추가
  - 페이지별 컨텍스트 텍스트 리스트 처리
  
- **새 메서드**: `extract_with_context()`
  - 하이브리드 방식 전용 메서드
  - PyMuPDF 텍스트 리스트를 받아 Vision API에 컨텍스트로 제공

### 2. `backend/services/pdf_processor.py`
- 파일 상단 주석 업데이트: 하이브리드 방식 설명 추가
- `_process_with_both_async()`: 완전히 재작성
  - 기존의 병합 로직 제거
  - PyMuPDF 텍스트를 Vision API 입력으로 활용
  - Vision 결과를 최종 결과로 사용

### 3. `backend/api/pdf.py`
- API 문서 업데이트
- `method="both"` 파라미터 설명 개선

## 🎯 프롬프트 변경

### 하이브리드 모드 프롬프트
```
다음은 이 페이지에서 추출된 텍스트입니다:
---
{PyMuPDF 텍스트}
---

위 텍스트를 **참고하여**, 이미지의 내용을 검증하고 보완해주세요.

**작업 지침:**
1. 텍스트 내용이 정확한지 이미지로 확인
2. **표 구조와 데이터**를 이미지 기반으로 정확히 검증 및 보완
3. **이미지/도식/그림**이 있다면 상세히 설명
4. 레이아웃 정보 (들여쓰기, 목록 구조 등) 보완
5. 특수 문자나 기호가 누락되었다면 추가
```

## 📊 메타데이터 변화

```json
{
  "method": "hybrid",
  "metadata": {
    "hybrid_mode": true,
    "pymupdf_chars": 1234,
    "vision_chars": 1456,
    "vision_tokens": 8500,
    "table_count": 5,
    "image_count": 3
  }
}
```

## 🧪 테스트 방법

### API 호출 예제
```bash
curl -X POST "http://localhost:8000/api/v1/pdf/upload" \
  -F "file=@sample.pdf" \
  -F "method=both" \
  -F "document_type=policy"
```

### 예상 흐름
1. PyMuPDF가 빠르게 텍스트 추출 (0.5초)
2. Vision API가 이미지+텍스트로 보완 (15초)
3. 최종 Markdown 결과 반환

## ⚠️ 주의사항

1. **기존 병합 로직 제거**: `HybridMerger.merge()`는 더 이상 하이브리드 모드에서 사용되지 않음
   - 하지만 코드는 유지 (향후 fallback용으로 활용 가능)
   
2. **토큰 사용량 증가**: 컨텍스트 텍스트가 추가되어 프롬프트 토큰이 증가할 수 있음
   - 하지만 Vision이 더 정확한 결과를 생성하여 전체적으로는 효율적
   
3. **처리 시간**: 하이브리드 모드는 PyMuPDF + Vision 모두 실행하므로 시간이 더 걸림
   - 정확도가 중요한 경우에만 사용 권장

## 🔍 비교

| 항목 | 기존 방식 | 새로운 방식 |
|------|----------|------------|
| PyMuPDF 역할 | 독립 실행 → 병합 | 컨텍스트 제공 |
| Vision API 역할 | 독립 실행 → 병합 | 텍스트 검증 + 보완 |
| 병합 로직 | 유사도 기반 선택 | 불필요 (단일 출력) |
| 표 정확도 | 중간 | 높음 |
| 이미지 설명 | 중간 | 높음 |
| 처리 복잡도 | 높음 | 중간 |

## 📚 관련 파일

- `backend/services/vision_extractor.py` - Vision API 추출 서비스
- `backend/services/pdf_processor.py` - PDF 처리 메인 서비스
- `backend/services/pymupdf_extractor.py` - PyMuPDF 추출 서비스
- `backend/services/hybrid_merger.py` - 병합 로직 (유지, fallback용)
- `backend/api/pdf.py` - PDF 업로드 API

## ✅ 완료 상태

- [x] VisionExtractor에 context_text 파라미터 추가
- [x] VisionExtractor.extract_with_context() 메서드 구현
- [x] PDFProcessor._process_with_both_async() 재작성
- [x] 프롬프트 개선 (하이브리드 모드용)
- [x] API 문서 업데이트
- [x] 린터 오류 없음 확인

---

**작성일**: 2025-10-21  
**변경 이유**: 약관 업로드 시 텍스트와 이미지를 함께 활용하여 정확도 향상

