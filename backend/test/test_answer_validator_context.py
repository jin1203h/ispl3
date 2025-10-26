"""
AnswerValidator 컨텍스트 일치도 확인 테스트

키워드 추출 및 컨텍스트 매칭 기능을 테스트합니다.
"""
import sys
import os
from pathlib import Path

# backend 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 테스트 환경 설정
os.environ["TESTING"] = "true"

from services.answer_validator import AnswerValidator
from models.answer_validation import ValidationDetail


def test_extract_keywords():
    """키워드 추출 테스트"""
    print("=" * 60)
    print("Test 1: 키워드 추출")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 1. 한글 키워드
    text1 = "암진단비는 최초 1회에 한하여 3000만원이 지급됩니다."
    keywords1 = validator._extract_keywords(text1)
    
    assert len(keywords1) > 0
    assert "암진단비는" in keywords1 or "암진단비" in keywords1
    assert "3000만원이" in keywords1 or "3000만원" in keywords1
    print(f"✅ 한글 키워드: {keywords1[:5]}...")
    
    # 2. 영문 키워드
    text2 = "The insurance policy covers cancer diagnosis."
    keywords2 = validator._extract_keywords(text2)
    
    assert len(keywords2) > 0
    assert any("insurance" in kw.lower() for kw in keywords2)
    print(f"✅ 영문 키워드: {keywords2}")
    
    # 3. 혼합 키워드
    text3 = "암진단비 cancer 3000만원 insurance"
    keywords3 = validator._extract_keywords(text3)
    
    assert len(keywords3) >= 2
    print(f"✅ 혼합 키워드: {keywords3}")
    
    # 4. 짧은 단어 필터링 (3글자 미만)
    text4 = "암 진단 AB 123"
    keywords4 = validator._extract_keywords(text4)
    
    # 3글자 이상만 추출되어야 함
    for kw in keywords4:
        assert len(kw) >= 3
    print(f"✅ 짧은 단어 필터링: {keywords4}")
    
    # 5. 빈 텍스트
    text5 = ""
    keywords5 = validator._extract_keywords(text5)
    
    assert len(keywords5) == 0
    print(f"✅ 빈 텍스트: {keywords5}")
    
    print()


def test_check_context_match_perfect():
    """컨텍스트 일치 - 완전 일치 테스트"""
    print("=" * 60)
    print("Test 2: 컨텍스트 일치 - 완전 일치")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 답변과 검색 결과가 완전히 일치
    answer = "암 진단 시 3000만원이 지급됩니다."
    search_results = [
        {"content": "제5조: 암 진단 시 3000만원이 지급됩니다."}
    ]
    
    result = validator._check_context_match(answer, search_results)
    
    assert isinstance(result, ValidationDetail)
    assert result.check_name == "컨텍스트 일치"
    # 완전 일치이므로 높은 점수
    assert result.score >= 0.7
    
    print(f"✅ 완전 일치:")
    print(f"   - passed: {result.passed}")
    print(f"   - score: {result.score:.2f}")
    print(f"   - details: {result.details}")
    print()


def test_check_context_match_partial():
    """컨텍스트 일치 - 부분 일치 테스트"""
    print("=" * 60)
    print("Test 3: 컨텍스트 일치 - 부분 일치")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 답변의 일부만 검색 결과에 포함
    answer = "암 진단비는 3000만원이고 입원비는 5만원입니다."
    search_results = [
        {"content": "제5조: 암 진단비는 3000만원입니다."}
        # "입원비"와 "5만원"은 없음
    ]
    
    result = validator._check_context_match(answer, search_results)
    
    assert isinstance(result, ValidationDetail)
    # 부분 일치이므로 중간 점수
    assert 0.0 < result.score < 1.0
    
    print(f"✅ 부분 일치:")
    print(f"   - passed: {result.passed}")
    print(f"   - score: {result.score:.2f}")
    print(f"   - details: {result.details}")
    print()


def test_check_context_match_no_match():
    """컨텍스트 일치 - 불일치 테스트"""
    print("=" * 60)
    print("Test 4: 컨텍스트 일치 - 불일치")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 답변과 검색 결과가 완전히 다름
    answer = "입원비는 일당 5만원입니다."
    search_results = [
        {"content": "제5조: 암 진단비는 3000만원입니다."}
        # "입원비", "일당", "5만원" 모두 없음
    ]
    
    result = validator._check_context_match(answer, search_results)
    
    assert isinstance(result, ValidationDetail)
    # 불일치이므로 낮은 점수
    assert result.score < 0.7
    
    print(f"✅ 불일치:")
    print(f"   - passed: {result.passed}")
    print(f"   - score: {result.score:.2f}")
    print(f"   - details: {result.details}")
    print()


def test_check_context_match_no_keywords():
    """컨텍스트 일치 - 키워드 없음 테스트"""
    print("=" * 60)
    print("Test 5: 컨텍스트 일치 - 키워드 없음")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 짧은 단어만 있는 답변 (키워드 추출 불가)
    answer = "네 네 네"
    search_results = [
        {"content": "제5조: 암 진단비 지급"}
    ]
    
    result = validator._check_context_match(answer, search_results)
    
    assert isinstance(result, ValidationDetail)
    # 키워드 없으면 N/A (1.0)
    assert result.score == 1.0
    assert result.passed == True
    assert "없음" in result.details
    
    print(f"✅ 키워드 없음:")
    print(f"   - passed: {result.passed}")
    print(f"   - score: {result.score}")
    print(f"   - details: {result.details}")
    print()


def test_check_context_match_no_results():
    """컨텍스트 일치 - 검색 결과 없음 테스트"""
    print("=" * 60)
    print("Test 6: 컨텍스트 일치 - 검색 결과 없음")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 검색 결과가 없음
    answer = "암 진단비는 3000만원입니다."
    search_results = []
    
    result = validator._check_context_match(answer, search_results)
    
    assert isinstance(result, ValidationDetail)
    # 검색 결과 없으면 0.0
    assert result.score == 0.0
    assert result.passed == False
    
    print(f"✅ 검색 결과 없음:")
    print(f"   - passed: {result.passed}")
    print(f"   - score: {result.score}")
    print(f"   - details: {result.details}")
    print()


def test_check_context_match_multiple_results():
    """컨텍스트 일치 - 여러 검색 결과 테스트"""
    print("=" * 60)
    print("Test 7: 컨텍스트 일치 - 여러 검색 결과")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 여러 검색 결과에 걸쳐 매칭
    answer = "암 진단비는 3000만원이고 입원비는 5만원입니다."
    search_results = [
        {"content": "제5조: 암 진단비는 3000만원입니다."},
        {"content": "제15조: 입원비는 일당 5만원입니다."}
    ]
    
    result = validator._check_context_match(answer, search_results)
    
    assert isinstance(result, ValidationDetail)
    # 여러 결과에 걸쳐 일치하므로 높은 점수
    assert result.score >= 0.7
    
    print(f"✅ 여러 검색 결과:")
    print(f"   - passed: {result.passed}")
    print(f"   - score: {result.score:.2f}")
    print(f"   - details: {result.details}")
    print()


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("AnswerValidator 컨텍스트 일치도 확인 테스트")
    print("=" * 60 + "\n")
    
    tests = [
        ("키워드 추출", test_extract_keywords),
        ("컨텍스트 일치 - 완전 일치", test_check_context_match_perfect),
        ("컨텍스트 일치 - 부분 일치", test_check_context_match_partial),
        ("컨텍스트 일치 - 불일치", test_check_context_match_no_match),
        ("컨텍스트 일치 - 키워드 없음", test_check_context_match_no_keywords),
        ("컨텍스트 일치 - 검색 결과 없음", test_check_context_match_no_results),
        ("컨텍스트 일치 - 여러 검색 결과", test_check_context_match_multiple_results),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
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

