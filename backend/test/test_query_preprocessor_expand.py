"""
QueryPreprocessor 동의어 확장 및 조항 번호 추출 테스트

동의어 확장과 조항 번호 추출 기능을 테스트합니다.
"""
import sys
import os
import asyncio
import logging
from pathlib import Path

# backend 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 테스트 환경 설정
os.environ["TESTING"] = "true"

from services.query_preprocessor import QueryPreprocessor

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_extract_clause_number():
    """조항 번호 추출 테스트"""
    print("=" * 60)
    print("Test 1: 조항 번호 추출")
    print("=" * 60)
    
    preprocessor = QueryPreprocessor()
    
    test_cases = [
        ("제15조의 내용", "제15조"),
        ("15조 보장", "제15조"),
        ("제 3 조", "제3조"),
        ("보험금 얼마", None),
        ("제100조", "제100조"),
    ]
    
    passed = 0
    for query, expected in test_cases:
        clause_number = preprocessor._extract_clause_number(query)
        if clause_number == expected:
            print(f"   ✓ '{query}' → {clause_number}")
            passed += 1
        else:
            print(f"   ✗ '{query}' → {clause_number} (예상: {expected})")
    
    assert passed == len(test_cases), f"조항 번호 추출 실패: {passed}/{len(test_cases)}"
    
    print(f"✅ 조항 번호 추출 테스트: {passed}/{len(test_cases)} 통과")
    print()


async def test_expand_synonyms():
    """동의어 확장 테스트"""
    print("=" * 60)
    print("Test 2: 동의어 확장")
    print("=" * 60)
    
    preprocessor = QueryPreprocessor()
    
    # "암" 동의어: ["악성신생물", "암질환"]
    query1 = "암 진단비 얼마"
    expanded1 = preprocessor._expand_synonyms(query1)
    
    assert query1 in expanded1, "원본 쿼리가 포함되지 않음"
    assert len(expanded1) >= 2, "동의어 확장이 되지 않음"
    
    print(f"   ✓ '{query1}'")
    for exp in expanded1:
        print(f"     → {exp}")
    
    # "보험금" 동의어: ["보험금액", "지급금", "보장금"]
    query2 = "보험금 지급"
    expanded2 = preprocessor._expand_synonyms(query2)
    
    assert query2 in expanded2, "원본 쿼리가 포함되지 않음"
    assert len(expanded2) >= 2, "동의어 확장이 되지 않음"
    
    print(f"   ✓ '{query2}'")
    for exp in expanded2:
        print(f"     → {exp}")
    
    # 동의어가 없는 경우
    query3 = "일반 텍스트"
    expanded3 = preprocessor._expand_synonyms(query3)
    
    assert len(expanded3) == 1, "동의어가 없을 때 원본만 반환해야 함"
    assert expanded3[0] == query3, "원본 쿼리가 유지되지 않음"
    
    print(f"   ✓ '{query3}' → 원본만 반환 (동의어 없음)")
    
    print(f"✅ 동의어 확장 테스트 통과")
    print()


async def test_preprocess_with_clause_number():
    """조항 번호가 있는 쿼리 전처리"""
    print("=" * 60)
    print("Test 3: 조항 번호 포함 쿼리")
    print("=" * 60)
    
    preprocessor = QueryPreprocessor()
    
    query = "제15조의 내용을 알려줘"
    result = await preprocessor.preprocess(query)
    
    assert result.original == query
    assert result.clause_number == "제15조", f"조항 번호 추출 실패: {result.clause_number}"
    assert isinstance(result.expanded_terms, list)
    assert len(result.expanded_terms) >= 1
    
    print(f"✅ 조항 번호 포함 쿼리 전처리:")
    print(f"   - original: {result.original}")
    print(f"   - standardized: {result.standardized}")
    print(f"   - clause_number: {result.clause_number}")
    print(f"   - expanded_terms: {len(result.expanded_terms)}개")
    print()


async def test_preprocess_with_synonyms():
    """동의어가 있는 쿼리 전처리"""
    print("=" * 60)
    print("Test 4: 동의어 확장 쿼리")
    print("=" * 60)
    
    preprocessor = QueryPreprocessor()
    
    query = "암진단비 얼마인가요?"
    result = await preprocessor.preprocess(query)
    
    assert result.original == query
    assert result.standardized == "암 진단비 얼마인가요?"
    assert len(result.expanded_terms) >= 2, "동의어 확장이 되지 않음"
    
    print(f"✅ 동의어 확장 쿼리 전처리:")
    print(f"   - original: {result.original}")
    print(f"   - standardized: {result.standardized}")
    print(f"   - expanded_terms:")
    for term in result.expanded_terms[:5]:  # 처음 5개만 출력
        print(f"     → {term}")
    print()


async def test_preprocess_combined():
    """조항 번호 + 동의어 조합 쿼리"""
    print("=" * 60)
    print("Test 5: 조항 번호 + 동의어")
    print("=" * 60)
    
    preprocessor = QueryPreprocessor()
    
    query = "제3조 암진단비"
    result = await preprocessor.preprocess(query)
    
    assert result.clause_number == "제3조", "조항 번호 추출 실패"
    assert result.standardized == "제3조 암 진단비", "전문용어 표준화 실패"
    assert len(result.expanded_terms) >= 2, "동의어 확장 실패"
    
    print(f"✅ 조합 쿼리 전처리:")
    print(f"   - original: {result.original}")
    print(f"   - standardized: {result.standardized}")
    print(f"   - clause_number: {result.clause_number}")
    print(f"   - expanded_terms: {len(result.expanded_terms)}개")
    for term in result.expanded_terms[:3]:
        print(f"     → {term}")
    print()


async def test_no_clause_no_synonyms():
    """조항 번호도 동의어도 없는 쿼리"""
    print("=" * 60)
    print("Test 6: 조항 번호 X, 동의어 X")
    print("=" * 60)
    
    preprocessor = QueryPreprocessor()
    
    query = "일반 질문입니다"
    result = await preprocessor.preprocess(query)
    
    assert result.clause_number is None, "조항 번호가 None이 아님"
    assert len(result.expanded_terms) == 1, "동의어가 없을 때 원본만 반환해야 함"
    assert result.expanded_terms[0] == query, "원본 쿼리가 유지되지 않음"
    
    print(f"✅ 조항/동의어 없는 쿼리:")
    print(f"   - original: {result.original}")
    print(f"   - clause_number: {result.clause_number}")
    print(f"   - expanded_terms: {result.expanded_terms}")
    print()


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("QueryPreprocessor 동의어 확장 및 조항 번호 추출 테스트")
    print("=" * 60 + "\n")
    
    tests = [
        ("조항 번호 추출", test_extract_clause_number),
        ("동의어 확장", test_expand_synonyms),
        ("조항 번호 포함 쿼리", test_preprocess_with_clause_number),
        ("동의어 확장 쿼리", test_preprocess_with_synonyms),
        ("조합 쿼리", test_preprocess_combined),
        ("조항/동의어 없음", test_no_clause_no_synonyms),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            asyncio.run(test_func())
            passed += 1
        except Exception as e:
            print(f"❌ {test_name} 실패: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("=" * 60)
    print(f"테스트 결과: {passed}개 통과, {failed}개 실패")
    print("=" * 60)
    
    if failed == 0:
        print("✅ 모든 테스트 통과!")
        return 0
    else:
        print(f"❌ {failed}개 테스트 실패")
        return 1


if __name__ == "__main__":
    exit(main())

