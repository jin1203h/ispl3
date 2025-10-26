"""
QueryPreprocessor 불완전 질의 감지 테스트

전체 전처리 파이프라인이 정상 작동하는지 테스트합니다.
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


async def test_incomplete_query_detection():
    """불완전 질의 감지 테스트"""
    print("=" * 60)
    print("Test 1: 불완전 질의 감지")
    print("=" * 60)
    
    preprocessor = QueryPreprocessor()
    
    # 불완전 질의 테스트
    incomplete_queries = ["얼마", "제15조", "언제", "어떻게", "보험"]
    
    for query in incomplete_queries:
        is_complete, suggestions = preprocessor._check_completeness(query)
        
        assert not is_complete, f"'{query}'가 불완전 질의로 감지되지 않음"
        assert len(suggestions) > 0, f"'{query}'에 대한 제안사항이 없음"
        
        print(f"   ✓ '{query}' → 불완전 (제안: {suggestions[0][:30]}...)")
    
    print(f"✅ 불완전 질의 감지: {len(incomplete_queries)}개 모두 감지")
    print()


async def test_complete_query_detection():
    """완전한 질의 감지 테스트"""
    print("=" * 60)
    print("Test 2: 완전한 질의 감지")
    print("=" * 60)
    
    preprocessor = QueryPreprocessor()
    
    # 완전한 질의 테스트
    complete_queries = [
        "암 진단비 얼마인가요?",
        "제15조의 내용을 알려주세요",
        "보험금 지급 조건은 무엇인가요?",
        "해지 환급금을 언제 받을 수 있나요?",
    ]
    
    for query in complete_queries:
        is_complete, suggestions = preprocessor._check_completeness(query)
        
        assert is_complete, f"'{query}'가 완전한 질의로 인식되지 않음"
        assert len(suggestions) == 0, f"'{query}'에 불필요한 제안사항이 있음"
        
        print(f"   ✓ '{query[:30]}...' → 완전")
    
    print(f"✅ 완전한 질의 감지: {len(complete_queries)}개 모두 감지")
    print()


async def test_incomplete_query_preprocess():
    """불완전 질의 전처리 결과 확인"""
    print("=" * 60)
    print("Test 3: 불완전 질의 전처리")
    print("=" * 60)
    
    preprocessor = QueryPreprocessor()
    
    query = "얼마"
    result = await preprocessor.preprocess(query)
    
    assert result.original == query
    assert not result.is_complete, "is_complete가 False가 아님"
    assert len(result.suggestions) > 0, "suggestions가 비어있음"
    
    print(f"✅ 불완전 질의 전처리:")
    print(f"   - original: {result.original}")
    print(f"   - is_complete: {result.is_complete}")
    print(f"   - suggestions: {result.suggestions[0][:50]}...")
    print()


async def test_complete_query_preprocess():
    """완전한 질의 전처리 결과 확인"""
    print("=" * 60)
    print("Test 4: 완전한 질의 전처리")
    print("=" * 60)
    
    preprocessor = QueryPreprocessor()
    
    query = "암 진단비 얼마인가요?"
    result = await preprocessor.preprocess(query)
    
    assert result.original == query
    assert result.is_complete, "is_complete가 True가 아님"
    assert len(result.suggestions) == 0, "suggestions가 비어있지 않음"
    
    print(f"✅ 완전한 질의 전처리:")
    print(f"   - original: {result.original}")
    print(f"   - is_complete: {result.is_complete}")
    print(f"   - suggestions: {result.suggestions}")
    print()


async def test_full_pipeline():
    """전체 전처리 파이프라인 테스트"""
    print("=" * 60)
    print("Test 5: 전체 파이프라인")
    print("=" * 60)
    
    preprocessor = QueryPreprocessor()
    
    # 모든 기능을 사용하는 쿼리
    query = "  제15조  암진단비  얼마인가요?  "
    result = await preprocessor.preprocess(query)
    
    # 모든 단계 확인
    assert result.original == query, "original 불일치"
    assert result.normalized == "제15조 암진단비 얼마인가요?", "normalized 불일치"
    assert result.standardized == "제15조 암 진단비 얼마인가요?", "standardized 불일치"
    assert len(result.expanded_terms) >= 2, "동의어 확장 실패"
    assert result.clause_number == "제15조", "조항 번호 추출 실패"
    assert result.is_complete, "완전성 판단 실패"
    assert len(result.suggestions) == 0, "불필요한 제안사항"
    
    print(f"✅ 전체 파이프라인 테스트:")
    print(f"   1. 정규화: '{result.normalized}'")
    print(f"   2. 표준화: '{result.standardized}'")
    print(f"   3. 동의어 확장: {len(result.expanded_terms)}개")
    print(f"   4. 조항 번호: {result.clause_number}")
    print(f"   5. 완전성: {result.is_complete}")
    print()


async def test_various_queries():
    """다양한 쿼리로 전처리 테스트"""
    print("=" * 60)
    print("Test 6: 다양한 쿼리")
    print("=" * 60)
    
    preprocessor = QueryPreprocessor()
    
    test_cases = [
        {
            "query": "보험금 지급은 언제인가요?",
            "expected_complete": True,
            "expected_clause": None,
        },
        {
            "query": "얼마",
            "expected_complete": False,
            "expected_clause": None,
        },
        {
            "query": "제3조 암진단비",
            "expected_complete": True,
            "expected_clause": "제3조",
        },
        {
            "query": "해지환급금 조회",
            "expected_complete": True,
            "expected_clause": None,
        },
    ]
    
    passed = 0
    for case in test_cases:
        query = case["query"]
        result = await preprocessor.preprocess(query)
        
        # 완전성 확인
        if result.is_complete == case["expected_complete"]:
            # 조항 번호 확인
            if result.clause_number == case["expected_clause"]:
                print(f"   ✓ '{query}' → is_complete={result.is_complete}, clause={result.clause_number}")
                passed += 1
            else:
                print(f"   ✗ '{query}' → clause={result.clause_number} (예상: {case['expected_clause']})")
        else:
            print(f"   ✗ '{query}' → is_complete={result.is_complete} (예상: {case['expected_complete']})")
    
    assert passed == len(test_cases), f"다양한 쿼리 테스트 실패: {passed}/{len(test_cases)}"
    
    print(f"✅ 다양한 쿼리 테스트: {passed}/{len(test_cases)} 통과")
    print()


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("QueryPreprocessor 불완전 질의 감지 및 전체 파이프라인 테스트")
    print("=" * 60 + "\n")
    
    tests = [
        ("불완전 질의 감지", test_incomplete_query_detection),
        ("완전한 질의 감지", test_complete_query_detection),
        ("불완전 질의 전처리", test_incomplete_query_preprocess),
        ("완전한 질의 전처리", test_complete_query_preprocess),
        ("전체 파이프라인", test_full_pipeline),
        ("다양한 쿼리", test_various_queries),
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

