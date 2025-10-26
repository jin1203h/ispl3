"""
AnswerValidator 기본 기능 테스트

AnswerValidator의 초기화, 형식 검증, validate() 파이프라인을 테스트합니다.
"""
import sys
import os
import asyncio
from pathlib import Path

# backend 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 테스트 환경 설정
os.environ["TESTING"] = "true"

from services.answer_validator import AnswerValidator
from models.answer_validation import ValidationDetail, AnswerValidation


def test_initialization():
    """AnswerValidator 초기화 테스트"""
    print("=" * 60)
    print("Test 1: 초기화")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    assert hasattr(validator, 'client'), "OpenAI client 없음"
    assert hasattr(validator, 'threshold'), "threshold 없음"
    assert validator.threshold == 0.7, f"threshold가 0.7이 아님: {validator.threshold}"
    assert hasattr(validator, 'WEIGHTS'), "WEIGHTS 없음"
    
    print(f"✅ 초기화 성공:")
    print(f"   - threshold: {validator.threshold}")
    print(f"   - weights: {validator.WEIGHTS}")
    print()


def test_format_check_good_answer():
    """형식 검증 - 좋은 답변 테스트"""
    print("=" * 60)
    print("Test 2: 형식 검증 - 좋은 답변")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 구조화, 참조, 조항 모두 포함
    answer = """**📌 답변**
암 진단비는 최초 1회에 한하여 3,000만원이 지급됩니다 [참조 1, 제5조].

**📋 관련 약관**
- [참조 1] 제5조(암진단비의 지급): 3,000만원 지급"""
    
    search_results = [
        {"content": "제5조...", "clause_number": "제5조"}
    ]
    
    result = validator._check_format(answer, search_results)
    
    assert isinstance(result, ValidationDetail)
    assert result.check_name == "형식 검증"
    assert result.passed == True, "형식 검증 실패"
    assert result.score >= 0.5, f"점수가 너무 낮음: {result.score}"
    
    print(f"✅ 형식 검증 통과:")
    print(f"   - passed: {result.passed}")
    print(f"   - score: {result.score}")
    print(f"   - details: {result.details}")
    print()


def test_format_check_bad_answer():
    """형식 검증 - 나쁜 답변 테스트"""
    print("=" * 60)
    print("Test 3: 형식 검증 - 나쁜 답변")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 구조화 없음, 참조 없음
    answer = "암 진단비는 3,000만원입니다."
    
    search_results = []
    
    result = validator._check_format(answer, search_results)
    
    assert isinstance(result, ValidationDetail)
    assert result.passed == False, "나쁜 답변이 통과됨"
    assert result.score < 1.0, f"점수가 너무 높음: {result.score}"
    
    print(f"✅ 형식 검증 실패 (예상됨):")
    print(f"   - passed: {result.passed}")
    print(f"   - score: {result.score}")
    print(f"   - details: {result.details}")
    print()


def test_format_check_partial():
    """형식 검증 - 부분 일치 테스트"""
    print("=" * 60)
    print("Test 4: 형식 검증 - 부분 일치")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 구조화는 있지만 참조 없음
    answer = """**📌 답변**
암 진단비는 3,000만원입니다.

**📋 관련 약관**
- 제5조: 암진단비 지급"""
    
    search_results = []
    
    result = validator._check_format(answer, search_results)
    
    assert isinstance(result, ValidationDetail)
    # 구조화는 있지만 참조 번호가 없으므로 실패
    assert result.passed == False
    
    print(f"✅ 부분 일치:")
    print(f"   - passed: {result.passed}")
    print(f"   - score: {result.score}")
    print(f"   - details: {result.details}")
    print()


async def test_validate_pipeline():
    """validate() 파이프라인 테스트"""
    print("=" * 60)
    print("Test 5: validate() 파이프라인")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    answer = """**📌 답변**
암 진단비는 최초 1회에 한하여 3,000만원이 지급됩니다 [참조 1].

**📋 관련 약관**
- [참조 1] 제5조: 암진단비 지급"""
    
    search_results = [
        {"content": "제5조...", "clause_number": "제5조"}
    ]
    
    # Mock session (None으로 테스트)
    validation = await validator.validate(answer, search_results, None)
    
    assert isinstance(validation, AnswerValidation)
    assert validation.confidence_score >= 0.0
    assert validation.confidence_score <= 1.0
    assert isinstance(validation.is_reliable, bool)
    assert validation.format_check.passed == True
    assert validation.validation_time > 0
    
    print(f"✅ validate() 파이프라인 통과:")
    print(f"   - confidence_score: {validation.confidence_score:.2f}")
    print(f"   - is_reliable: {validation.is_reliable}")
    print(f"   - format_check.passed: {validation.format_check.passed}")
    print(f"   - validation_time: {validation.validation_time:.3f}s")
    print()


async def test_validate_low_score():
    """validate() 낮은 점수 테스트"""
    print("=" * 60)
    print("Test 6: validate() 낮은 점수")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 형식이 나쁜 답변
    answer = "암 진단비는 3,000만원입니다."
    search_results = []
    
    validation = await validator.validate(answer, search_results, None)
    
    assert isinstance(validation, AnswerValidation)
    assert validation.format_check.passed == False
    # 현재는 나머지가 임시값 0.5이므로 전체 점수는 중간
    assert validation.confidence_score < 1.0
    
    print(f"✅ 낮은 점수:")
    print(f"   - confidence_score: {validation.confidence_score:.2f}")
    print(f"   - is_reliable: {validation.is_reliable}")
    print(f"   - format_check.score: {validation.format_check.score}")
    print()


async def test_validate_error_handling():
    """validate() 오류 처리 테스트"""
    print("=" * 60)
    print("Test 7: validate() 오류 처리")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 잘못된 입력 (None)
    try:
        validation = await validator.validate(None, [], None)
        
        # 오류 발생 시에도 AnswerValidation 반환
        assert isinstance(validation, AnswerValidation)
        assert validation.confidence_score == 0.5
        assert validation.is_reliable == False
        assert len(validation.warnings) > 0
        
        print(f"✅ 오류 처리:")
        print(f"   - confidence_score: {validation.confidence_score}")
        print(f"   - warnings: {validation.warnings}")
    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        raise
    
    print()


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("AnswerValidator 기본 기능 테스트")
    print("=" * 60 + "\n")
    
    sync_tests = [
        ("초기화", test_initialization),
        ("형식 검증 - 좋은 답변", test_format_check_good_answer),
        ("형식 검증 - 나쁜 답변", test_format_check_bad_answer),
        ("형식 검증 - 부분 일치", test_format_check_partial),
    ]
    
    async_tests = [
        ("validate() 파이프라인", test_validate_pipeline),
        ("validate() 낮은 점수", test_validate_low_score),
        ("validate() 오류 처리", test_validate_error_handling),
    ]
    
    passed = 0
    failed = 0
    
    # 동기 테스트
    for test_name, test_func in sync_tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_name} 실패: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # 비동기 테스트
    for test_name, test_func in async_tests:
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

