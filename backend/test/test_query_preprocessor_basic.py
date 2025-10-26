"""
QueryPreprocessor 기본 기능 테스트

정규화 및 전문용어 표준화 기능을 테스트합니다.
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
from models.preprocessed_query import PreprocessedQuery

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_initialization():
    """QueryPreprocessor 초기화 테스트"""
    print("=" * 60)
    print("Test 1: 초기화")
    print("=" * 60)
    
    preprocessor = QueryPreprocessor()
    
    # 전문용어 사전 로딩 확인
    assert preprocessor.term_dictionary is not None, "전문용어 사전이 로딩되지 않음"
    assert len(preprocessor.spacing_rules) > 0, "spacing_rules가 비어있음"
    assert len(preprocessor.synonym_dict) > 0, "synonym_dict가 비어있음"
    assert len(preprocessor.incomplete_patterns) > 0, "incomplete_patterns가 비어있음"
    
    print(f"✅ 초기화 완료:")
    print(f"   - spacing_rules: {len(preprocessor.spacing_rules)}개")
    print(f"   - synonyms: {len(preprocessor.synonym_dict)}개")
    print(f"   - patterns: {len(preprocessor.incomplete_patterns)}개")
    print()


async def test_normalize():
    """공백 정규화 테스트"""
    print("=" * 60)
    print("Test 2: 공백 정규화")
    print("=" * 60)
    
    preprocessor = QueryPreprocessor()
    
    test_cases = [
        ("  암진단비  ", "암진단비"),
        ("암  진단비", "암 진단비"),
        ("보험료   납입", "보험료 납입"),
        ("  여러    공백    테스트  ", "여러 공백 테스트"),
    ]
    
    passed = 0
    for original, expected in test_cases:
        normalized = preprocessor._normalize(original)
        if normalized == expected:
            print(f"   ✓ '{original}' → '{normalized}'")
            passed += 1
        else:
            print(f"   ✗ '{original}' → '{normalized}' (예상: '{expected}')")
    
    assert passed == len(test_cases), f"공백 정규화 실패: {passed}/{len(test_cases)}"
    
    print(f"✅ 공백 정규화 테스트: {passed}/{len(test_cases)} 통과")
    print()


async def test_standardize_terms():
    """전문용어 표준화 테스트"""
    print("=" * 60)
    print("Test 3: 전문용어 표준화")
    print("=" * 60)
    
    preprocessor = QueryPreprocessor()
    
    test_cases = [
        ("암진단비", "암 진단비"),
        ("보험금액", "보험 금액"),
        ("해지환급금", "해지 환급금"),
        ("암진단비와 수술비", "암 진단비와 수술비"),
        ("일반 텍스트", "일반 텍스트"),  # 변경 없음
    ]
    
    passed = 0
    for original, expected in test_cases:
        standardized = preprocessor._standardize_terms(original)
        if standardized == expected:
            print(f"   ✓ '{original}' → '{standardized}'")
            passed += 1
        else:
            print(f"   ✗ '{original}' → '{standardized}' (예상: '{expected}')")
    
    assert passed == len(test_cases), f"전문용어 표준화 실패: {passed}/{len(test_cases)}"
    
    print(f"✅ 전문용어 표준화 테스트: {passed}/{len(test_cases)} 통과")
    print()


async def test_preprocess_pipeline():
    """전체 전처리 파이프라인 테스트"""
    print("=" * 60)
    print("Test 4: 전처리 파이프라인")
    print("=" * 60)
    
    preprocessor = QueryPreprocessor()
    
    test_cases = [
        ("  암진단비  얼마인가요?  ", "암 진단비 얼마인가요?"),
        ("보험금액   조회", "보험 금액 조회"),
        ("해지환급금은 얼마인가요", "해지 환급금은 얼마인가요"),
    ]
    
    passed = 0
    for original, expected_standardized in test_cases:
        result = await preprocessor.preprocess(original)
        
        # 검증
        assert result.original == original, "original 불일치"
        assert isinstance(result.normalized, str), "normalized가 문자열이 아님"
        assert isinstance(result.standardized, str), "standardized가 문자열이 아님"
        assert isinstance(result.expanded_terms, list), "expanded_terms가 리스트가 아님"
        assert result.clause_number is None, "clause_number가 None이 아님 (다음 task)"
        assert result.is_complete is True, "is_complete가 True가 아님 (다음 task)"
        assert result.suggestions == [], "suggestions가 비어있지 않음 (다음 task)"
        
        if result.standardized == expected_standardized:
            print(f"   ✓ '{original}' → '{result.standardized}'")
            passed += 1
        else:
            print(f"   ✗ '{original}' → '{result.standardized}' (예상: '{expected_standardized}')")
    
    assert passed == len(test_cases), f"전처리 파이프라인 실패: {passed}/{len(test_cases)}"
    
    print(f"✅ 전처리 파이프라인 테스트: {passed}/{len(test_cases)} 통과")
    print()


async def test_error_handling():
    """에러 처리 (fallback) 테스트"""
    print("=" * 60)
    print("Test 5: 에러 처리")
    print("=" * 60)
    
    preprocessor = QueryPreprocessor()
    
    # 정상적인 쿼리로 테스트 (에러 발생 시 fallback 확인)
    query = "정상 쿼리"
    result = await preprocessor.preprocess(query)
    
    assert result.original == query, "fallback 시 original 유지 실패"
    assert isinstance(result, PreprocessedQuery), "PreprocessedQuery 객체가 아님"
    
    print(f"✅ 에러 처리 (fallback) 테스트 통과")
    print(f"   - 정상 쿼리에 대해 PreprocessedQuery 반환 확인")
    print()


async def test_preprocess_result_structure():
    """PreprocessedQuery 결과 구조 테스트"""
    print("=" * 60)
    print("Test 6: 결과 구조")
    print("=" * 60)
    
    preprocessor = QueryPreprocessor()
    
    query = "암진단비 얼마인가요?"
    result = await preprocessor.preprocess(query)
    
    # 필드 존재 확인
    assert hasattr(result, 'original'), "original 필드 없음"
    assert hasattr(result, 'normalized'), "normalized 필드 없음"
    assert hasattr(result, 'standardized'), "standardized 필드 없음"
    assert hasattr(result, 'expanded_terms'), "expanded_terms 필드 없음"
    assert hasattr(result, 'clause_number'), "clause_number 필드 없음"
    assert hasattr(result, 'is_complete'), "is_complete 필드 없음"
    assert hasattr(result, 'suggestions'), "suggestions 필드 없음"
    
    # 값 확인
    assert result.original == query
    assert result.standardized == "암 진단비 얼마인가요?"
    assert len(result.expanded_terms) > 0
    
    print(f"✅ 결과 구조 테스트 통과:")
    print(f"   - original: {result.original}")
    print(f"   - standardized: {result.standardized}")
    print(f"   - expanded_terms: {result.expanded_terms}")
    print()


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("QueryPreprocessor 기본 기능 테스트 시작")
    print("=" * 60 + "\n")
    
    tests = [
        ("초기화", test_initialization),
        ("공백 정규화", test_normalize),
        ("전문용어 표준화", test_standardize_terms),
        ("전처리 파이프라인", test_preprocess_pipeline),
        ("에러 처리", test_error_handling),
        ("결과 구조", test_preprocess_result_structure),
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

