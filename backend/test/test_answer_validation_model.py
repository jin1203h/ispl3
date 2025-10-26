"""
AnswerValidation 모델 테스트

ValidationDetail과 AnswerValidation Pydantic 모델의 
생성, 검증, 직렬화 기능을 테스트합니다.
"""
import sys
from pathlib import Path

# backend 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from models.answer_validation import ValidationDetail, AnswerValidation


def test_validation_detail_creation():
    """ValidationDetail 모델 생성 테스트"""
    print("=" * 60)
    print("Test 1: ValidationDetail 생성")
    print("=" * 60)
    
    detail = ValidationDetail(
        check_name="할루시네이션 검증",
        passed=True,
        score=0.9,
        details="모든 진술이 컨텍스트에 근거함"
    )
    
    assert detail.check_name == "할루시네이션 검증"
    assert detail.passed == True
    assert detail.score == 0.9
    assert detail.details == "모든 진술이 컨텍스트에 근거함"
    
    print(f"✅ ValidationDetail 생성: {detail.check_name}, score={detail.score}")
    print()


def test_validation_detail_score_validation():
    """ValidationDetail 점수 범위 검증 테스트"""
    print("=" * 60)
    print("Test 2: ValidationDetail 점수 범위 검증")
    print("=" * 60)
    
    # 정상 범위 (0.0 ~ 1.0)
    detail1 = ValidationDetail(
        check_name="테스트",
        passed=True,
        score=0.0
    )
    assert detail1.score == 0.0
    print(f"✅ score=0.0 허용")
    
    detail2 = ValidationDetail(
        check_name="테스트",
        passed=True,
        score=1.0
    )
    assert detail2.score == 1.0
    print(f"✅ score=1.0 허용")
    
    # 비정상 범위 (음수, >1.0)
    try:
        ValidationDetail(
            check_name="테스트",
            passed=True,
            score=-0.1
        )
        assert False, "음수 점수가 허용되면 안 됨"
    except Exception as e:
        print(f"✅ score=-0.1 거부: {type(e).__name__}")
    
    try:
        ValidationDetail(
            check_name="테스트",
            passed=True,
            score=1.1
        )
        assert False, "1.0 초과 점수가 허용되면 안 됨"
    except Exception as e:
        print(f"✅ score=1.1 거부: {type(e).__name__}")
    
    print()


def test_answer_validation_creation():
    """AnswerValidation 모델 생성 테스트"""
    print("=" * 60)
    print("Test 3: AnswerValidation 생성")
    print("=" * 60)
    
    hallucination = ValidationDetail(
        check_name="할루시네이션 검증",
        passed=True,
        score=0.9,
        details="모든 진술이 컨텍스트에 근거함"
    )
    
    clause = ValidationDetail(
        check_name="조항 존재 확인",
        passed=True,
        score=1.0,
        details="제5조, 제15조 모두 존재 확인"
    )
    
    context = ValidationDetail(
        check_name="컨텍스트 일치",
        passed=True,
        score=0.85,
        details="주요 내용 일치율 85%"
    )
    
    format_check = ValidationDetail(
        check_name="형식 검증",
        passed=True,
        score=1.0,
        details="구조화, 참조, 조항 모두 포함"
    )
    
    validation = AnswerValidation(
        confidence_score=0.85,
        is_reliable=True,
        hallucination_check=hallucination,
        clause_existence_check=clause,
        context_match_check=context,
        format_check=format_check,
        validation_time=0.8
    )
    
    assert validation.confidence_score == 0.85
    assert validation.is_reliable == True
    assert validation.regeneration_count == 0  # 기본값
    assert validation.warnings == []  # 기본값
    
    print(f"✅ AnswerValidation 생성: confidence={validation.confidence_score:.2f}")
    print(f"   - is_reliable: {validation.is_reliable}")
    print(f"   - regeneration_count: {validation.regeneration_count}")
    print(f"   - validation_time: {validation.validation_time}s")
    print()


def test_answer_validation_serialization():
    """AnswerValidation 직렬화 테스트"""
    print("=" * 60)
    print("Test 4: AnswerValidation 직렬화")
    print("=" * 60)
    
    validation = AnswerValidation(
        confidence_score=0.75,
        is_reliable=True,
        hallucination_check=ValidationDetail(
            check_name="할루시네이션",
            passed=True,
            score=0.8
        ),
        clause_existence_check=ValidationDetail(
            check_name="조항 존재",
            passed=True,
            score=0.9
        ),
        context_match_check=ValidationDetail(
            check_name="컨텍스트",
            passed=True,
            score=0.7
        ),
        format_check=ValidationDetail(
            check_name="형식",
            passed=True,
            score=1.0
        ),
        validation_time=0.5,
        regeneration_count=1,
        warnings=["경고 메시지 테스트"]
    )
    
    # dict() 직렬화
    data = validation.dict()
    
    assert isinstance(data, dict)
    assert data["confidence_score"] == 0.75
    assert data["is_reliable"] == True
    assert data["regeneration_count"] == 1
    assert len(data["warnings"]) == 1
    assert "hallucination_check" in data
    assert isinstance(data["hallucination_check"], dict)
    
    print(f"✅ dict() 직렬화 성공")
    print(f"   - confidence_score: {data['confidence_score']}")
    print(f"   - regeneration_count: {data['regeneration_count']}")
    print(f"   - warnings: {data['warnings']}")
    
    # JSON 직렬화
    import json
    json_str = validation.json()
    assert isinstance(json_str, str)
    
    # JSON 역직렬화
    parsed = json.loads(json_str)
    assert parsed["confidence_score"] == 0.75
    
    print(f"✅ JSON 직렬화/역직렬화 성공")
    print()


def test_answer_validation_repr():
    """AnswerValidation __repr__ 테스트"""
    print("=" * 60)
    print("Test 5: AnswerValidation __repr__")
    print("=" * 60)
    
    validation = AnswerValidation(
        confidence_score=0.85,
        is_reliable=True,
        hallucination_check=ValidationDetail(
            check_name="할루시네이션",
            passed=True,
            score=0.9
        ),
        clause_existence_check=ValidationDetail(
            check_name="조항",
            passed=True,
            score=1.0
        ),
        context_match_check=ValidationDetail(
            check_name="컨텍스트",
            passed=True,
            score=0.85
        ),
        format_check=ValidationDetail(
            check_name="형식",
            passed=True,
            score=1.0
        ),
        validation_time=0.8,
        regeneration_count=2
    )
    
    repr_str = repr(validation)
    
    assert "AnswerValidation" in repr_str
    assert "confidence=0.85" in repr_str
    assert "reliable=True" in repr_str
    assert "regeneration=2" in repr_str
    
    print(f"✅ __repr__ 출력:")
    print(f"   {repr_str}")
    print()


def test_low_confidence_validation():
    """낮은 신뢰도 AnswerValidation 테스트"""
    print("=" * 60)
    print("Test 6: 낮은 신뢰도 검증")
    print("=" * 60)
    
    validation = AnswerValidation(
        confidence_score=0.55,
        is_reliable=False,  # 0.7 미만
        hallucination_check=ValidationDetail(
            check_name="할루시네이션",
            passed=False,
            score=0.4,
            details="일부 진술이 컨텍스트에 근거하지 않음"
        ),
        clause_existence_check=ValidationDetail(
            check_name="조항",
            passed=False,
            score=0.5,
            details="제10조가 존재하지 않음"
        ),
        context_match_check=ValidationDetail(
            check_name="컨텍스트",
            passed=True,
            score=0.75
        ),
        format_check=ValidationDetail(
            check_name="형식",
            passed=True,
            score=1.0
        ),
        validation_time=0.6,
        warnings=["조항 번호 미존재", "할루시네이션 의심"]
    )
    
    assert validation.confidence_score == 0.55
    assert validation.is_reliable == False
    assert len(validation.warnings) == 2
    assert not validation.hallucination_check.passed
    assert not validation.clause_existence_check.passed
    
    print(f"✅ 낮은 신뢰도 검증:")
    print(f"   - confidence_score: {validation.confidence_score}")
    print(f"   - is_reliable: {validation.is_reliable}")
    print(f"   - warnings: {validation.warnings}")
    print()


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("AnswerValidation 모델 테스트")
    print("=" * 60 + "\n")
    
    tests = [
        ("ValidationDetail 생성", test_validation_detail_creation),
        ("ValidationDetail 점수 검증", test_validation_detail_score_validation),
        ("AnswerValidation 생성", test_answer_validation_creation),
        ("AnswerValidation 직렬화", test_answer_validation_serialization),
        ("AnswerValidation __repr__", test_answer_validation_repr),
        ("낮은 신뢰도 검증", test_low_confidence_validation),
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

