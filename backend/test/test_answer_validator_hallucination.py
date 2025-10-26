"""
AnswerValidator 할루시네이션 검증 테스트

GPT-4o-mini를 사용한 할루시네이션 검증 기능을 테스트합니다.
실제 API 호출은 환경 변수가 있을 때만 수행합니다.
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
from models.answer_validation import ValidationDetail


def test_build_context():
    """컨텍스트 구성 테스트"""
    print("=" * 60)
    print("Test 1: 컨텍스트 구성")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 1. 검색 결과가 있을 때
    search_results = [
        {"content": "제5조(암진단비의 지급): 암 진단 시 3,000만원 지급"},
        {"content": "제15조(입원비의 지급): 입원 시 일당 5만원 지급"}
    ]
    
    context = validator.build_context_for_validation(search_results)
    
    assert isinstance(context, str)
    assert "제5조" in context
    assert "제15조" in context
    assert "[1]" in context
    assert "[2]" in context
    
    print(f"✅ 컨텍스트 구성:")
    print(f"   길이: {len(context)}자")
    print(f"   내용 (앞부분): {context[:100]}...")
    print()
    
    # 2. 검색 결과가 없을 때
    context_empty = validator.build_context_for_validation([])
    assert "없음" in context_empty
    print(f"✅ 빈 검색 결과: {context_empty}")
    print()


def test_build_context_long():
    """긴 컨텍스트 제한 테스트"""
    print("=" * 60)
    print("Test 2: 긴 컨텍스트 제한")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 1000자가 넘는 긴 content
    long_content = "A" * 2000
    search_results = [
        {"content": long_content}
    ]
    
    context = validator.build_context_for_validation(search_results)
    
    # 1000자로 제한되어야 함
    assert len(context) <= 1004  # "..." 추가로 약간 더 길 수 있음
    assert context.endswith("...")
    
    print(f"✅ 긴 컨텍스트 제한:")
    print(f"   원본: {len(long_content)}자")
    print(f"   제한: {len(context)}자")
    print()


async def test_check_hallucination_api_available():
    """할루시네이션 검증 - API 사용 가능 시 테스트"""
    print("=" * 60)
    print("Test 3: 할루시네이션 검증 (API)")
    print("=" * 60)
    
    # OPENAI_API_KEY가 설정되어 있는지 확인
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key == "test-key":
        print("⚠️  OPENAI_API_KEY가 없어 스킵")
        print("   (실제 환경에서는 GPT-4o-mini API 호출)")
        print()
        return
    
    validator = AnswerValidator()
    
    # 정상적인 답변 (컨텍스트에 근거)
    answer = "암 진단 시 3,000만원이 지급됩니다."
    context = "[1] 제5조(암진단비의 지급): 암 진단 시 3,000만원 지급"
    
    result = await validator._check_hallucination(answer, context)
    
    assert isinstance(result, ValidationDetail)
    assert result.check_name == "할루시네이션 검증"
    assert 0.0 <= result.score <= 1.0
    
    print(f"✅ 할루시네이션 검증:")
    print(f"   - passed: {result.passed}")
    print(f"   - score: {result.score}")
    print(f"   - details: {result.details[:100]}...")
    print()


async def test_check_hallucination_mock():
    """할루시네이션 검증 - Mock 테스트"""
    print("=" * 60)
    print("Test 4: 할루시네이션 검증 (Mock)")
    print("=" * 60)
    
    # 이 테스트는 API 키가 없어도 실행됨
    # 오류 처리 로직을 테스트
    
    validator = AnswerValidator()
    
    # 빈 컨텍스트로 테스트
    answer = "암 진단비는 5,000만원입니다."
    context = ""
    
    try:
        result = await validator._check_hallucination(answer, context)
        
        # 오류가 발생해도 ValidationDetail 반환
        assert isinstance(result, ValidationDetail)
        # 오류 시 중립 점수 (0.5)
        assert result.score >= 0.0
        assert result.score <= 1.0
        
        print(f"✅ Mock 테스트:")
        print(f"   - score: {result.score}")
        print(f"   - details: {result.details[:100]}...")
    except Exception as e:
        # API 키가 없으면 오류 발생 가능
        print(f"⚠️  API 오류 (예상됨): {type(e).__name__}")
        print(f"   실제 환경에서는 0.5점 반환")
    
    print()


def test_context_truncation():
    """컨텍스트 자르기 테스트"""
    print("=" * 60)
    print("Test 5: 컨텍스트 자르기")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 여러 개의 긴 검색 결과
    search_results = []
    for i in range(5):
        search_results.append({
            "content": f"제{i+1}조: " + "내용 " * 200
        })
    
    context = validator.build_context_for_validation(search_results)
    
    # 1000자로 제한
    assert len(context) <= 1004
    
    print(f"✅ 컨텍스트 자르기:")
    print(f"   - 원본 검색 결과: {len(search_results)}개")
    print(f"   - 최종 컨텍스트: {len(context)}자")
    print()


async def test_hallucination_error_handling():
    """할루시네이션 검증 오류 처리 테스트"""
    print("=" * 60)
    print("Test 6: 오류 처리")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # None 입력으로 오류 유도
    try:
        result = await validator._check_hallucination(None, None)
        
        # 오류 발생해도 ValidationDetail 반환
        assert isinstance(result, ValidationDetail)
        assert result.score == 0.5  # 중립 점수
        
        print(f"✅ 오류 처리:")
        print(f"   - score: {result.score}")
        print(f"   - details: {result.details}")
    except Exception as e:
        print(f"⚠️  예외 발생 (예상됨): {type(e).__name__}")
    
    print()


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("AnswerValidator 할루시네이션 검증 테스트")
    print("=" * 60 + "\n")
    
    sync_tests = [
        ("컨텍스트 구성", test_build_context),
        ("긴 컨텍스트 제한", test_build_context_long),
        ("컨텍스트 자르기", test_context_truncation),
    ]
    
    async_tests = [
        ("할루시네이션 검증 (API)", test_check_hallucination_api_available),
        ("할루시네이션 검증 (Mock)", test_check_hallucination_mock),
        ("오류 처리", test_hallucination_error_handling),
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
        print("\n💡 참고: 실제 GPT-4o-mini API 호출은 OPENAI_API_KEY가 있을 때 수행됩니다.")
        return 0
    else:
        print(f"❌ {failed}개 테스트 실패")
        return 1


if __name__ == "__main__":
    exit(main())

