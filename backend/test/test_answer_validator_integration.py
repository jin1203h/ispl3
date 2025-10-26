"""
AnswerValidator 통합 테스트

전체 검증 파이프라인 및 신뢰도 점수 계산을 테스트합니다.
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
from models.answer_validation import AnswerValidation, ValidationDetail


def test_calculate_confidence():
    """신뢰도 점수 계산 테스트"""
    print("=" * 60)
    print("Test 1: 신뢰도 점수 계산")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 모든 검증이 통과한 경우
    hallucination = ValidationDetail(check_name="할루시네이션", passed=True, score=1.0)
    clause = ValidationDetail(check_name="조항", passed=True, score=1.0)
    context = ValidationDetail(check_name="컨텍스트", passed=True, score=1.0)
    format_check = ValidationDetail(check_name="형식", passed=True, score=1.0)
    
    confidence = validator._calculate_confidence(hallucination, clause, context, format_check)
    
    # 부동소수점 정밀도 문제로 약간의 오차 허용
    assert abs(confidence - 1.0) < 0.01
    print(f"✅ 모두 통과 (1.0): {confidence:.2f}")
    
    # 일부만 통과한 경우
    hallucination2 = ValidationDetail(check_name="할루시네이션", passed=True, score=0.8)
    clause2 = ValidationDetail(check_name="조항", passed=False, score=0.5)
    context2 = ValidationDetail(check_name="컨텍스트", passed=True, score=0.7)
    format2 = ValidationDetail(check_name="형식", passed=True, score=1.0)
    
    confidence2 = validator._calculate_confidence(hallucination2, clause2, context2, format2)
    
    # 0.8*0.4 + 0.5*0.2 + 0.7*0.3 + 1.0*0.1 = 0.32 + 0.1 + 0.21 + 0.1 = 0.73
    expected = 0.8*0.4 + 0.5*0.2 + 0.7*0.3 + 1.0*0.1
    assert abs(confidence2 - expected) < 0.01
    print(f"✅ 부분 통과 ({expected:.2f}): {confidence2:.2f}")
    
    # 모두 실패한 경우
    hallucination3 = ValidationDetail(check_name="할루시네이션", passed=False, score=0.0)
    clause3 = ValidationDetail(check_name="조항", passed=False, score=0.0)
    context3 = ValidationDetail(check_name="컨텍스트", passed=False, score=0.0)
    format3 = ValidationDetail(check_name="형식", passed=False, score=0.0)
    
    confidence3 = validator._calculate_confidence(hallucination3, clause3, context3, format3)
    
    assert confidence3 == 0.0
    print(f"✅ 모두 실패 (0.0): {confidence3}")
    
    print()


async def test_validate_high_quality():
    """고품질 답변 검증 테스트"""
    print("=" * 60)
    print("Test 2: 고품질 답변 검증")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 완벽한 답변
    answer = """**📌 답변**
암 진단비는 최초 1회에 한하여 3,000만원이 지급됩니다 [참조 1, 제5조].

**📋 관련 약관**
- [참조 1] 제5조(암진단비의 지급): 피보험자가 암으로 진단 확정되었을 때 3,000만원 지급
"""
    
    search_results = [
        {
            "content": "제5조(암진단비의 지급): 피보험자가 암으로 진단 확정되었을 때 최초 1회에 한하여 3,000만원을 지급합니다.",
            "clause_number": "제5조"
        }
    ]
    
    validation = await validator.validate(answer, search_results, None)
    
    assert isinstance(validation, AnswerValidation)
    assert validation.confidence_score >= 0.0
    assert validation.confidence_score <= 1.0
    assert validation.format_check.passed == True
    assert validation.validation_time > 0
    
    print(f"✅ 고품질 답변 검증:")
    print(f"   - confidence_score: {validation.confidence_score:.2f}")
    print(f"   - is_reliable: {validation.is_reliable}")
    print(f"   - format: {validation.format_check.score:.2f}")
    print(f"   - clause: {validation.clause_existence_check.score:.2f}")
    print(f"   - context: {validation.context_match_check.score:.2f}")
    print(f"   - validation_time: {validation.validation_time:.3f}s")
    print()


async def test_validate_low_quality():
    """저품질 답변 검증 테스트"""
    print("=" * 60)
    print("Test 3: 저품질 답변 검증")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 형식이 나쁜 답변
    answer = "암 진단비는 5,000만원입니다."  # 참조 없음, 구조화 없음
    
    search_results = [
        {
            "content": "제5조: 암 진단비는 3,000만원입니다.",
            "clause_number": "제5조"
        }
    ]
    
    validation = await validator.validate(answer, search_results, None)
    
    assert isinstance(validation, AnswerValidation)
    assert validation.format_check.passed == False
    # 형식이 나쁘므로 전체 점수도 낮아야 함
    assert validation.confidence_score < 1.0
    
    print(f"✅ 저품질 답변 검증:")
    print(f"   - confidence_score: {validation.confidence_score:.2f}")
    print(f"   - is_reliable: {validation.is_reliable}")
    print(f"   - format: {validation.format_check.score:.2f}")
    print()


async def test_validate_performance():
    """검증 성능 테스트"""
    print("=" * 60)
    print("Test 4: 검증 성능")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    answer = """**📌 답변**
테스트 답변입니다 [참조 1].

**📋 관련 약관**
- [참조 1] 테스트 내용
"""
    
    search_results = [{"content": "테스트 내용"}]
    
    import time
    start = time.time()
    
    validation = await validator.validate(answer, search_results, None)
    
    elapsed = time.time() - start
    
    assert isinstance(validation, AnswerValidation)
    # 순차 실행이지만 5초 이내에 완료되어야 함
    assert elapsed < 5.0
    
    print(f"✅ 검증 성능:")
    print(f"   - 소요 시간: {elapsed:.3f}s")
    print(f"   - validation_time: {validation.validation_time:.3f}s")
    print()


async def test_validate_threshold():
    """신뢰도 임계값 테스트"""
    print("=" * 60)
    print("Test 5: 신뢰도 임계값")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # threshold는 0.7
    assert validator.threshold == 0.7
    
    # 다양한 품질의 답변 테스트
    answers = [
        ("좋은 답변", """**📌 답변**
암 진단비는 3,000만원입니다 [참조 1].

**📋 관련 약관**
- [참조 1] 제5조: 암 진단비 3,000만원""", [{"content": "제5조: 암 진단비 3,000만원"}]),
        
        ("나쁜 답변", "암 진단비", [{"content": "제5조: 암 진단비"}]),
    ]
    
    for name, answer, results in answers:
        validation = await validator.validate(answer, results, None)
        print(f"   {name}: confidence={validation.confidence_score:.2f}, reliable={validation.is_reliable}")
    
    print()


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("AnswerValidator 통합 테스트")
    print("=" * 60 + "\n")
    
    sync_tests = [
        ("신뢰도 점수 계산", test_calculate_confidence),
    ]
    
    async_tests = [
        ("고품질 답변 검증", test_validate_high_quality),
        ("저품질 답변 검증", test_validate_low_quality),
        ("검증 성능", test_validate_performance),
        ("신뢰도 임계값", test_validate_threshold),
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

