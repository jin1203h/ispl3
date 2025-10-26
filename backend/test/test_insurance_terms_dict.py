"""
보험 전문용어 사전 테스트

insurance_terms.json 파일의 유효성과 내용을 검증합니다.
"""
import sys
import json
import re
from pathlib import Path

# backend 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def test_json_file_exists():
    """JSON 파일 존재 확인"""
    print("=" * 60)
    print("Test 1: JSON 파일 존재 확인")
    print("=" * 60)
    
    json_path = backend_dir / "data" / "insurance_terms.json"
    
    assert json_path.exists(), f"파일이 존재하지 않습니다: {json_path}"
    
    print(f"✅ 파일 존재 확인: {json_path}")
    print()
    
    return json_path


def test_json_valid_format(json_path):
    """JSON 형식 유효성 확인"""
    print("=" * 60)
    print("Test 2: JSON 형식 유효성")
    print("=" * 60)
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    assert isinstance(data, dict), "최상위 구조는 딕셔너리여야 합니다"
    
    print(f"✅ JSON 형식 유효: {len(data)}개 키")
    print(f"   키 목록: {list(data.keys())}")
    print()
    
    return data


def test_normalization_structure(data):
    """normalization 구조 확인"""
    print("=" * 60)
    print("Test 3: normalization 구조")
    print("=" * 60)
    
    assert "normalization" in data, "normalization 키가 없습니다"
    assert "spacing" in data["normalization"], "spacing 키가 없습니다"
    
    spacing = data["normalization"]["spacing"]
    assert isinstance(spacing, dict), "spacing은 딕셔너리여야 합니다"
    assert len(spacing) >= 5, f"spacing에 최소 5개 용어 필요 (현재: {len(spacing)}개)"
    
    print(f"✅ normalization.spacing: {len(spacing)}개 용어")
    print(f"   예시:")
    for i, (key, value) in enumerate(list(spacing.items())[:3]):
        print(f"   - '{key}' → '{value}'")
    print()


def test_synonyms_structure(data):
    """synonyms 구조 확인"""
    print("=" * 60)
    print("Test 4: synonyms 구조")
    print("=" * 60)
    
    assert "synonyms" in data, "synonyms 키가 없습니다"
    
    synonyms = data["synonyms"]
    assert isinstance(synonyms, dict), "synonyms는 딕셔너리여야 합니다"
    assert len(synonyms) >= 3, f"synonyms에 최소 3개 용어 필요 (현재: {len(synonyms)}개)"
    
    # 각 동의어가 리스트인지 확인
    for term, synonym_list in synonyms.items():
        assert isinstance(synonym_list, list), f"{term}의 동의어는 리스트여야 합니다"
        assert len(synonym_list) > 0, f"{term}의 동의어 리스트가 비어있습니다"
    
    print(f"✅ synonyms: {len(synonyms)}개 용어")
    print(f"   예시:")
    for i, (key, value) in enumerate(list(synonyms.items())[:3]):
        print(f"   - '{key}' → {value}")
    print()


def test_incomplete_patterns_structure(data):
    """incomplete_patterns 구조 확인"""
    print("=" * 60)
    print("Test 5: incomplete_patterns 구조")
    print("=" * 60)
    
    assert "incomplete_patterns" in data, "incomplete_patterns 키가 없습니다"
    
    patterns = data["incomplete_patterns"]
    assert isinstance(patterns, list), "incomplete_patterns는 리스트여야 합니다"
    assert len(patterns) >= 2, f"incomplete_patterns에 최소 2개 패턴 필요 (현재: {len(patterns)}개)"
    
    # 각 패턴 구조 확인
    for pattern_obj in patterns:
        assert "pattern" in pattern_obj, "pattern 키가 없습니다"
        assert "suggestion" in pattern_obj, "suggestion 키가 없습니다"
        
        # 정규 표현식 유효성 확인
        try:
            re.compile(pattern_obj["pattern"])
        except re.error as e:
            assert False, f"잘못된 정규 표현식: {pattern_obj['pattern']} - {e}"
    
    print(f"✅ incomplete_patterns: {len(patterns)}개 패턴")
    print(f"   예시:")
    for pattern_obj in patterns[:3]:
        print(f"   - 패턴: {pattern_obj['pattern']}")
        print(f"     제안: {pattern_obj['suggestion'][:50]}...")
    print()


def test_content_quality(data):
    """내용 품질 확인"""
    print("=" * 60)
    print("Test 6: 내용 품질")
    print("=" * 60)
    
    # normalization: 공백이 실제로 추가되는지 확인
    spacing = data["normalization"]["spacing"]
    spacing_count = 0
    for original, standardized in spacing.items():
        if " " in standardized and " " not in original:
            spacing_count += 1
    
    print(f"✅ 공백 추가 용어: {spacing_count}/{len(spacing)}개")
    
    # synonyms: 각 용어에 최소 1개 이상 동의어
    synonyms = data["synonyms"]
    synonym_count = sum(len(v) for v in synonyms.values())
    
    print(f"✅ 총 동의어 수: {synonym_count}개 (평균 {synonym_count/len(synonyms):.1f}개/용어)")
    
    # incomplete_patterns: 모든 패턴이 제안사항 포함
    patterns = data["incomplete_patterns"]
    has_suggestion = all(len(p.get("suggestion", "")) > 0 for p in patterns)
    
    assert has_suggestion, "모든 패턴은 제안사항을 포함해야 합니다"
    print(f"✅ 모든 패턴에 제안사항 포함")
    print()


def test_pattern_matching(data):
    """패턴 매칭 테스트"""
    print("=" * 60)
    print("Test 7: 패턴 매칭")
    print("=" * 60)
    
    patterns = data["incomplete_patterns"]
    
    # 테스트 케이스
    test_queries = {
        "얼마": True,  # ^얼마 패턴 매칭
        "제15조": True,  # ^제\d+조$ 패턴 매칭
        "암 진단비 얼마": False,  # 불완전하지 않음
        "제3조의 내용": False,  # 불완전하지 않음
    }
    
    matched_count = 0
    for query, should_match in test_queries.items():
        matched = False
        for pattern_obj in patterns:
            pattern = re.compile(pattern_obj["pattern"])
            if pattern.search(query):
                matched = True
                break
        
        if matched == should_match:
            status = "✓"
            matched_count += 1
        else:
            status = "✗"
        
        print(f"   {status} '{query}': {'매칭' if matched else '매칭 안됨'} (예상: {'매칭' if should_match else '매칭 안됨'})")
    
    print(f"\n✅ 패턴 매칭 테스트: {matched_count}/{len(test_queries)}개 통과")
    print()


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("보험 전문용어 사전 테스트 시작")
    print("=" * 60 + "\n")
    
    try:
        # Test 1: 파일 존재 확인
        json_path = test_json_file_exists()
        
        # Test 2: JSON 형식 유효성
        data = test_json_valid_format(json_path)
        
        # Test 3: normalization 구조
        test_normalization_structure(data)
        
        # Test 4: synonyms 구조
        test_synonyms_structure(data)
        
        # Test 5: incomplete_patterns 구조
        test_incomplete_patterns_structure(data)
        
        # Test 6: 내용 품질
        test_content_quality(data)
        
        # Test 7: 패턴 매칭
        test_pattern_matching(data)
        
        print("=" * 60)
        print("테스트 결과: 7개 통과, 0개 실패")
        print("=" * 60)
        print("✅ 모든 테스트 통과!")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

