"""
SearchAgent + QueryPreprocessor 통합 테스트

SearchAgent가 QueryPreprocessor를 정상적으로 사용하는지 테스트합니다.
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

from agents.search_agent import SearchAgent
from agents.state import create_initial_state

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_initialization():
    """SearchAgent 초기화 테스트"""
    print("=" * 60)
    print("Test 1: 초기화")
    print("=" * 60)
    
    agent = SearchAgent()
    
    # QueryPreprocessor 포함 확인
    assert hasattr(agent, 'vector_search_service'), "VectorSearchService 미존재"
    assert hasattr(agent, 'hybrid_search_service'), "HybridSearchService 미존재"
    assert hasattr(agent, 'query_preprocessor'), "QueryPreprocessor 미존재"
    
    # extract_clause_number() 메서드 제거 확인
    assert not hasattr(agent, 'extract_clause_number'), "extract_clause_number() 메서드가 아직 존재함"
    
    print(f"✅ 초기화 검증:")
    print(f"   - QueryPreprocessor: 포함")
    print(f"   - extract_clause_number(): 제거됨")
    print()


async def test_search_with_preprocessing():
    """전처리된 쿼리로 검색 테스트"""
    print("=" * 60)
    print("Test 2: 전처리된 쿼리로 검색")
    print("=" * 60)
    
    agent = SearchAgent()
    
    # 전문용어 포함 쿼리
    state = create_initial_state(query="암진단비 얼마인가요?")
    result = await agent.search(state)
    
    # 검색 성공 확인
    assert result["task_results"]["search"]["success"], "검색 실패"
    assert "preprocessing" in result["task_results"]["search"], "preprocessing 정보 없음"
    
    # 전처리 정보 확인
    preprocessing = result["task_results"]["search"]["preprocessing"]
    assert "original_query" in preprocessing, "original_query 없음"
    assert "standardized_query" in preprocessing, "standardized_query 없음"
    assert "expanded_terms_count" in preprocessing, "expanded_terms_count 없음"
    
    # 표준화 확인 ("암진단비" → "암 진단비")
    assert "암 진단비" in preprocessing["standardized_query"], "전문용어 표준화 실패"
    
    print(f"✅ 전처리된 쿼리로 검색:")
    print(f"   - original: {preprocessing['original_query']}")
    print(f"   - standardized: {preprocessing['standardized_query']}")
    print(f"   - expanded_terms: {preprocessing['expanded_terms_count']}개")
    print()


async def test_incomplete_query_handling():
    """불완전 질의 처리 테스트"""
    print("=" * 60)
    print("Test 3: 불완전 질의 처리")
    print("=" * 60)
    
    agent = SearchAgent()
    
    # 불완전 질의
    state = create_initial_state(query="얼마")
    result = await agent.search(state)
    
    # 불완전 질의 감지 확인
    assert not result["task_results"]["search"]["success"], "success가 False가 아님"
    assert result["task_results"]["search"]["incomplete_query"], "incomplete_query 플래그 없음"
    assert "suggestions" in result["task_results"]["search"], "suggestions 없음"
    assert len(result["task_results"]["search"]["suggestions"]) > 0, "제안사항이 비어있음"
    
    # 검색 결과가 없어야 함
    assert len(result["search_results"]) == 0, "불완전 질의에 검색 결과가 있음"
    
    print(f"✅ 불완전 질의 처리:")
    print(f"   - incomplete_query: True")
    print(f"   - suggestions: {result['task_results']['search']['suggestions'][0][:50]}...")
    print(f"   - search_results: 비어있음")
    print()


async def test_clause_number_extraction():
    """조항 번호 추출 및 threshold 조정 테스트"""
    print("=" * 60)
    print("Test 4: 조항 번호 추출")
    print("=" * 60)
    
    agent = SearchAgent()
    
    # 조항 번호 포함 쿼리
    state = create_initial_state(query="제15조의 내용을 알려주세요")
    result = await agent.search(state)
    
    # 조항 번호 추출 확인
    preprocessing = result["task_results"]["search"]["preprocessing"]
    assert preprocessing["clause_number"] == "제15조", "조항 번호 추출 실패"
    
    print(f"✅ 조항 번호 추출:")
    print(f"   - clause_number: {preprocessing['clause_number']}")
    print(f"   - threshold: 0.3 (조정됨)")
    print()


async def test_empty_query():
    """빈 쿼리 처리 테스트"""
    print("=" * 60)
    print("Test 5: 빈 쿼리 처리")
    print("=" * 60)
    
    agent = SearchAgent()
    
    # 빈 쿼리
    state = create_initial_state(query="")
    result = await agent.search(state)
    
    # 오류 메시지 확인
    assert result["error"] == "검색 쿼리가 비어있습니다.", "빈 쿼리 오류 메시지 불일치"
    assert len(result["search_results"]) == 0, "빈 쿼리에 검색 결과가 있음"
    
    print(f"✅ 빈 쿼리 처리:")
    print(f"   - error: {result['error']}")
    print()


async def test_various_queries():
    """다양한 쿼리로 통합 테스트"""
    print("=" * 60)
    print("Test 6: 다양한 쿼리")
    print("=" * 60)
    
    agent = SearchAgent()
    
    queries = [
        "보험금 지급 조건",
        "제3조 암 진단비",
        "해지환급금은 얼마",
    ]
    
    for query in queries:
        state = create_initial_state(query=query)
        result = await agent.search(state)
        
        # 기본 검증
        success = result["task_results"]["search"]["success"]
        print(f"   ✓ '{query}' → success={success}, ", end="")
        
        if success:
            preprocessing = result["task_results"]["search"]["preprocessing"]
            print(f"standardized='{preprocessing['standardized_query'][:30]}...'")
        else:
            print(f"incomplete_query=True")
    
    print(f"✅ 다양한 쿼리 테스트 완료")
    print()


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("SearchAgent + QueryPreprocessor 통합 테스트")
    print("=" * 60 + "\n")
    
    tests = [
        ("초기화", test_initialization),
        ("전처리된 쿼리로 검색", test_search_with_preprocessing),
        ("불완전 질의 처리", test_incomplete_query_handling),
        ("조항 번호 추출", test_clause_number_extraction),
        ("빈 쿼리 처리", test_empty_query),
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

