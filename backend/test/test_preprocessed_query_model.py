"""
PreprocessedQuery 모델 테스트

Pydantic 모델의 검증 및 기능을 테스트합니다.
"""
import sys
from pathlib import Path

# backend 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from models.preprocessed_query import PreprocessedQuery
from pydantic import ValidationError


def test_model_creation():
    """PreprocessedQuery 모델 생성 테스트"""
    print("=" * 60)
    print("Test 1: 모델 생성")
    print("=" * 60)
    
    query = PreprocessedQuery(
        original="암진단비 얼마인가요?",
        normalized="암진단비 얼마인가요?",
        standardized="암 진단비 얼마인가요?",
        expanded_terms=["암 진단비 얼마인가요?", "악성신생물 진단비 얼마인가요?"],
        clause_number=None,
        is_complete=True,
        suggestions=[]
    )
    
    assert query.original == "암진단비 얼마인가요?"
    assert query.normalized == "암진단비 얼마인가요?"
    assert query.standardized == "암 진단비 얼마인가요?"
    assert len(query.expanded_terms) == 2
    assert query.clause_number is None
    assert query.is_complete is True
    assert query.suggestions == []
    
    print(f"✅ 모델 생성 성공: {query}")
    print()


def test_model_with_clause_number():
    """조항 번호가 있는 경우 테스트"""
    print("=" * 60)
    print("Test 2: 조항 번호 포함")
    print("=" * 60)
    
    query = PreprocessedQuery(
        original="제15조의 내용",
        normalized="제15조의 내용",
        standardized="제15조의 내용",
        expanded_terms=["제15조의 내용"],
        clause_number="제15조",
        is_complete=True,
        suggestions=[]
    )
    
    assert query.clause_number == "제15조"
    
    print(f"✅ 조항 번호 포함 성공: clause_number={query.clause_number}")
    print()


def test_incomplete_query():
    """불완전 질의 테스트"""
    print("=" * 60)
    print("Test 3: 불완전 질의")
    print("=" * 60)
    
    query = PreprocessedQuery(
        original="얼마",
        normalized="얼마",
        standardized="얼마",
        expanded_terms=["얼마"],
        clause_number=None,
        is_complete=False,
        suggestions=["구체적인 항목을 추가해주세요. 예: '암 진단비 얼마인가요?'"]
    )
    
    assert query.is_complete is False
    assert len(query.suggestions) == 1
    
    print(f"✅ 불완전 질의 테스트 성공: is_complete={query.is_complete}")
    print(f"   제안사항: {query.suggestions[0]}")
    print()


def test_default_values():
    """기본값 테스트"""
    print("=" * 60)
    print("Test 4: 기본값")
    print("=" * 60)
    
    query = PreprocessedQuery(
        original="암",
        normalized="암",
        standardized="암",
        is_complete=True
    )
    
    assert query.expanded_terms == []
    assert query.clause_number is None
    assert query.suggestions == []
    
    print(f"✅ 기본값 테스트 성공: expanded_terms={query.expanded_terms}, suggestions={query.suggestions}")
    print()


def test_required_fields_validation():
    """필수 필드 검증 테스트"""
    print("=" * 60)
    print("Test 5: 필수 필드 검증")
    print("=" * 60)
    
    try:
        # original 누락
        query = PreprocessedQuery(
            normalized="test",
            standardized="test",
            is_complete=True
        )
        print("❌ ValidationError가 발생하지 않음")
        assert False, "original 필드 누락 시 ValidationError가 발생해야 함"
    except ValidationError as e:
        print(f"✅ 필수 필드 누락 시 ValidationError 발생: {e.error_count()}개 오류")
    
    print()


def test_field_access():
    """필드 접근 테스트"""
    print("=" * 60)
    print("Test 6: 필드 접근")
    print("=" * 60)
    
    query = PreprocessedQuery(
        original="보험금",
        normalized="보험금",
        standardized="보험금",
        expanded_terms=["보험금", "보험금액", "지급금"],
        clause_number=None,
        is_complete=True,
        suggestions=[]
    )
    
    # 필드 개별 접근
    assert query.original == "보험금"
    assert query.standardized == "보험금"
    assert len(query.expanded_terms) == 3
    assert "보험금액" in query.expanded_terms
    
    # dict 변환
    query_dict = query.model_dump()
    assert query_dict["original"] == "보험금"
    assert len(query_dict["expanded_terms"]) == 3
    
    print(f"✅ 필드 접근 및 dict 변환 성공")
    print(f"   dict keys: {list(query_dict.keys())}")
    print()


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("PreprocessedQuery 모델 테스트 시작")
    print("=" * 60 + "\n")
    
    tests = [
        ("모델 생성", test_model_creation),
        ("조항 번호 포함", test_model_with_clause_number),
        ("불완전 질의", test_incomplete_query),
        ("기본값", test_default_values),
        ("필수 필드 검증", test_required_fields_validation),
        ("필드 접근", test_field_access),
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

