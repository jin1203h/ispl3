"""
키워드 추출 테스트 스크립트

형태소 분석기 기반 키워드 추출을 테스트합니다.
"""
import sys
from pathlib import Path

# backend 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from utils.text_utils import extract_keywords


def test_keyword_extraction():
    """키워드 추출 테스트"""
    
    test_cases = [
        # (질의, 기대 키워드, 설명)
        ("면책기간은?", ["면책기간"], "단일 복합명사"),
        ("면책기간은 얼마나 되나요?", ["면책기간"], "의문사 제거"),
        ("경계성종양이란?", ["경계성종양"], "복합명사 유지"),
        ("경계성 종양이란?", ["경계성", "종양"], "띄어쓰기 있음"),
        ("갑상선암진단비는?", ["갑상선암진단비"], "긴 복합명사 유지"),  # ✅ 수정
        ("암보험은 보험금을 언제 받나요?", ["암보험", "보험금"], "의문사/조사 제거"),
        ("입원했을 때 입원비는?", ["입원", "입원비"], "활용형 처리"),
        ("보험금 지급 거절 사유는?", ["보험금", "지급", "거절", "사유"], "띄어쓰기로 분리된 명사들"),
        ("호스피스의 신청은 어떻게?", ["호스피스", "신청"], "조사/의문사 제거"),
    ]
    
    print("=" * 60)
    print("키워드 추출 테스트 (Kiwi 형태소 분석기)")
    print("=" * 60)
    
    success = 0
    total = len(test_cases)
    
    for idx, (query, expected, desc) in enumerate(test_cases, 1):
        result = extract_keywords(query)
        
        print(f"\n[테스트 {idx}] {desc}")
        print(f"  질의: {query}")
        print(f"  추출: {result}")
        print(f"  기대: {expected}")
        
        # 기대값과 일치하는지 확인
        is_success = result == expected
        
        if is_success:
            print(f"  결과: ✅ PASS")
            success += 1
        else:
            print(f"  결과: ❌ FAIL")
    
    print("\n" + "=" * 60)
    print(f"테스트 결과: {success}/{total} 성공 ({success/total*100:.1f}%)")
    print("=" * 60)
    
    return success == total


if __name__ == "__main__":
    try:
        success = test_keyword_extraction()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

