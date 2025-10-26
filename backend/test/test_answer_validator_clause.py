"""
AnswerValidator 조항 번호 존재 확인 테스트

조항 번호 추출, DB 쿼리, 존재 여부 검증을 테스트합니다.
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


def test_extract_clause_numbers():
    """조항 번호 추출 테스트"""
    print("=" * 60)
    print("Test 1: 조항 번호 추출")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 1. 단일 조항
    answer1 = "제5조에 따르면..."
    clauses1 = validator._extract_clause_numbers(answer1)
    assert "제5조" in clauses1
    print(f"✅ 단일 조항: {clauses1}")
    
    # 2. 여러 조항
    answer2 = "제5조와 제15조에 따르면..."
    clauses2 = validator._extract_clause_numbers(answer2)
    assert "제5조" in clauses2
    assert "제15조" in clauses2
    print(f"✅ 여러 조항: {clauses2}")
    
    # 3. 공백 포함
    answer3 = "제 5 조, 제 15 조"
    clauses3 = validator._extract_clause_numbers(answer3)
    assert "제5조" in clauses3
    assert "제15조" in clauses3
    print(f"✅ 공백 포함: {clauses3}")
    
    # 4. 중복 제거
    answer4 = "제5조는... 제5조에서..."
    clauses4 = validator._extract_clause_numbers(answer4)
    assert len(clauses4) == 1
    assert "제5조" in clauses4
    print(f"✅ 중복 제거: {clauses4}")
    
    # 5. 조항 없음
    answer5 = "조항 번호가 없습니다."
    clauses5 = validator._extract_clause_numbers(answer5)
    assert len(clauses5) == 0
    print(f"✅ 조항 없음: {clauses5}")
    
    print()


async def test_check_clause_existence_no_clauses():
    """조항 존재 확인 - 조항 없음 테스트"""
    print("=" * 60)
    print("Test 2: 조항 존재 확인 - 조항 없음")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    answer = "조항 번호가 없는 답변입니다."
    
    result = await validator._check_clause_existence(answer, None)
    
    assert isinstance(result, ValidationDetail)
    assert result.passed == True
    assert result.score == 1.0
    assert "없음" in result.details
    
    print(f"✅ 조항 없음 처리:")
    print(f"   - passed: {result.passed}")
    print(f"   - score: {result.score}")
    print(f"   - details: {result.details}")
    print()


async def test_check_clause_existence_no_session():
    """조항 존재 확인 - 세션 없음 테스트"""
    print("=" * 60)
    print("Test 3: 조항 존재 확인 - 세션 없음")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    answer = "제5조에 따르면..."
    
    result = await validator._check_clause_existence(answer, None)
    
    assert isinstance(result, ValidationDetail)
    assert result.score == 0.5
    assert "세션" in result.details or "검증 불가" in result.details
    
    print(f"✅ 세션 없음 처리:")
    print(f"   - passed: {result.passed}")
    print(f"   - score: {result.score}")
    print(f"   - details: {result.details}")
    print()


def test_extract_multiple_clauses():
    """여러 조항 추출 테스트"""
    print("=" * 60)
    print("Test 4: 여러 조항 추출")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    answer = """**📌 답변**
제5조에 따라 암 진단비 3,000만원이 지급되며 [참조 1], 
제15조에 따라 입원비가 보장됩니다 [참조 2].

**📋 관련 약관**
- [참조 1] 제5조: 암진단비 지급
- [참조 2] 제15조: 입원비 지급
"""
    
    clauses = validator._extract_clause_numbers(answer)
    
    assert len(clauses) >= 2
    assert "제5조" in clauses
    assert "제15조" in clauses
    
    print(f"✅ 여러 조항 추출: {sorted(clauses)}")
    print()


def test_extract_clause_patterns():
    """다양한 조항 패턴 추출 테스트"""
    print("=" * 60)
    print("Test 5: 다양한 조항 패턴")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    patterns = [
        ("제5조", ["제5조"]),
        ("제 5 조", ["제5조"]),
        ("제5조제2항", ["제5조"]),
        ("제5조, 제15조", ["제5조", "제15조"]),
        ("제5조는... 제5조가...", ["제5조"]),  # 중복
    ]
    
    for answer, expected in patterns:
        clauses = validator._extract_clause_numbers(answer)
        for exp in expected:
            assert exp in clauses, f"{exp}가 {clauses}에 없음"
        print(f"✅ '{answer}' → {clauses}")
    
    print()


async def test_clause_existence_score_calculation():
    """조항 존재 확인 점수 계산 테스트 (Mock)"""
    print("=" * 60)
    print("Test 6: 점수 계산 로직")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 점수 계산 로직 검증 (Mock DB 없이)
    # _extract_clause_numbers만 테스트
    
    answer1 = "제5조"
    clauses1 = validator._extract_clause_numbers(answer1)
    print(f"✅ 단일 조항 추출: {clauses1} (1개)")
    assert len(clauses1) == 1
    
    answer2 = "제5조, 제10조, 제15조"
    clauses2 = validator._extract_clause_numbers(answer2)
    print(f"✅ 다수 조항 추출: {clauses2} (3개)")
    assert len(clauses2) == 3
    
    # 실제 점수 계산은 DB 연동 테스트에서 확인
    # score = len(existing) / len(mentioned)
    # 예: 3개 중 2개 존재 → 0.67
    # 예: 3개 모두 존재 → 1.0
    
    print()


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("AnswerValidator 조항 번호 존재 확인 테스트")
    print("=" * 60 + "\n")
    
    sync_tests = [
        ("조항 번호 추출", test_extract_clause_numbers),
        ("여러 조항 추출", test_extract_multiple_clauses),
        ("다양한 조항 패턴", test_extract_clause_patterns),
    ]
    
    async_tests = [
        ("조항 존재 확인 - 조항 없음", test_check_clause_existence_no_clauses),
        ("조항 존재 확인 - 세션 없음", test_check_clause_existence_no_session),
        ("점수 계산 로직", test_clause_existence_score_calculation),
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
    import asyncio
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
        print("\n💡 참고: DB 연동 테스트는 실제 데이터가 있을 때 수행됩니다.")
        return 0
    else:
        print(f"❌ {failed}개 테스트 실패")
        return 1


if __name__ == "__main__":
    exit(main())

