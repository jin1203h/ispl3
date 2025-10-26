"""
SearchAgent 하이브리드 검색 통합 테스트

SearchAgent가 HybridSearchService를 정상적으로 호출하고
task_results에 total_tokens와 search_type이 포함되는지 검증합니다.
"""
import sys
import os
from pathlib import Path
import asyncio
import logging

# backend 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 테스트 환경 설정
os.environ["TESTING"] = "true"

from sqlalchemy.ext.asyncio import AsyncSession

from agents.search_agent import SearchAgent
from agents.state import ISPLState, create_initial_state
from core.database import AsyncSessionLocal
from models import Document, DocumentChunk

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_search_agent_initialization():
    """SearchAgent가 HybridSearchService를 포함하여 정상 초기화되는지 확인"""
    agent = SearchAgent()
    
    # VectorSearchService와 HybridSearchService가 모두 있는지 확인
    assert hasattr(agent, 'vector_search_service'), "VectorSearchService 미존재"
    assert hasattr(agent, 'hybrid_search_service'), "HybridSearchService 미존재"
    
    logger.info("✅ SearchAgent 초기화 검증 완료")


async def test_search_agent_hybrid_search():
    """SearchAgent가 하이브리드 검색을 수행하고 올바른 결과를 반환하는지 확인"""
    agent = SearchAgent()
    
    # 테스트 상태 생성
    state = create_initial_state(query="보험 약관")
    
    # 검색 수행
    result = await agent.search(state)
    
    # 기본 필드 확인
    assert "search_results" in result, "search_results 필드 누락"
    assert "task_results" in result, "task_results 필드 누락"
    assert "next_agent" in result, "next_agent 필드 누락"
    assert "error" in result, "error 필드 누락"
    
    # next_agent 확인
    assert result["next_agent"] == "answer_agent", "next_agent가 answer_agent가 아님"
    
    # task_results 구조 확인
    search_task = result["task_results"].get("search", {})
    assert search_task.get("success") is True, "검색 실패"
    assert "count" in search_task, "count 필드 누락"
    assert "query" in search_task, "query 필드 누락"
    assert "total_tokens" in search_task, "total_tokens 필드 누락"  # 하이브리드 검색 추가 필드
    assert "search_type" in search_task, "search_type 필드 누락"  # 하이브리드 검색 추가 필드
    
    # search_type이 'hybrid'인지 확인
    assert search_task["search_type"] == "hybrid", "search_type이 hybrid가 아님"
    
    # total_tokens이 양수인지 확인
    assert search_task["total_tokens"] >= 0, "total_tokens이 음수"
    
    logger.info(f"✅ 하이브리드 검색 결과: {search_task['count']}개, {search_task['total_tokens']}토큰")


async def test_search_agent_with_clause_number():
    """SearchAgent가 조항 번호 쿼리를 처리하는지 확인"""
    agent = SearchAgent()
    
    # 조항 번호 추출 확인
    clause_number = agent.extract_clause_number("제15조의 내용을 알려줘")
    assert clause_number == "제15조", f"조항 번호 추출 실패: {clause_number}"
    
    # 검색 수행
    state = create_initial_state(query="제15조의 내용을 알려줘")
    result = await agent.search(state)
    
    # 검색 결과 확인
    assert result["task_results"]["search"]["success"] is True, "검색 실패"
    assert result["task_results"]["search"]["search_type"] == "hybrid", "search_type이 hybrid가 아님"
    
    logger.info("✅ 조항 번호 쿼리 처리 검증 완료")


async def test_search_agent_empty_query():
    """SearchAgent가 빈 쿼리를 처리하는지 확인"""
    agent = SearchAgent()
    
    # 빈 쿼리로 검색
    state = create_initial_state(query="")
    result = await agent.search(state)
    
    # 오류 확인
    assert result["error"] == "검색 쿼리가 비어있습니다.", "빈 쿼리 오류 메시지 불일치"
    assert result["search_results"] == [], "빈 쿼리 시 search_results가 비어있지 않음"
    
    logger.info("✅ 빈 쿼리 처리 검증 완료")


async def test_search_agent_multiple_queries():
    """SearchAgent가 여러 쿼리를 연속으로 처리하는지 확인"""
    agent = SearchAgent()
    
    queries = [
        "암 진단비",
        "보험료 납입",
        "제3조",
        "해지환급금"
    ]
    
    for query in queries:
        state = create_initial_state(query=query)
        result = await agent.search(state)
        
        # 기본 검증
        assert result["task_results"]["search"]["success"] is True, f"검색 실패: {query}"
        assert result["task_results"]["search"]["search_type"] == "hybrid", "search_type이 hybrid가 아님"
        assert result["task_results"]["search"]["query"] == query, "쿼리 불일치"
        
        logger.info(
            f"  쿼리: '{query}' → "
            f"{result['task_results']['search']['count']}개 결과, "
            f"{result['task_results']['search']['total_tokens']}토큰"
        )
    
    logger.info("✅ 여러 쿼리 연속 처리 검증 완료")


async def test_search_agent_token_limits():
    """SearchAgent가 토큰 제한을 준수하는지 확인"""
    agent = SearchAgent()
    
    # 긴 쿼리 (많은 결과를 반환할 가능성이 높음)
    state = create_initial_state(query="보험 약관 조항 내용")
    result = await agent.search(state)
    
    # task_results 확인
    search_task = result["task_results"]["search"]
    total_tokens = search_task["total_tokens"]
    
    # 토큰 수가 8000 이하인지 확인 (컨텍스트 최적화)
    assert total_tokens <= 8000, f"토큰 제한 초과: {total_tokens}토큰"
    
    logger.info(f"✅ 토큰 제한 준수 검증 완료: {total_tokens}토큰")


async def test_search_agent_state_compatibility():
    """SearchAgent 결과가 AnswerAgent와 호환되는지 확인"""
    agent = SearchAgent()
    
    state = create_initial_state(query="암 진단비")
    result = await agent.search(state)
    
    # search_results가 리스트인지 확인
    assert isinstance(result["search_results"], list), "search_results가 리스트가 아님"
    
    # 각 결과가 딕셔너리인지 확인
    for search_result in result["search_results"]:
        assert isinstance(search_result, dict), "검색 결과가 딕셔너리가 아님"
        
        # AnswerAgent가 필요로 하는 필드 확인
        required_fields = [
            "chunk_id", "document_id", "content", "similarity",
            "chunk_type", "page_number", "clause_number", "document"
        ]
        for field in required_fields:
            assert field in search_result, f"필수 필드 누락: {field}"
    
    logger.info("✅ AnswerAgent 호환성 검증 완료")


def main():
    """모든 테스트를 순차적으로 실행"""
    logger.info("=" * 60)
    logger.info("SearchAgent 하이브리드 검색 통합 테스트 시작")
    logger.info("=" * 60)
    
    tests = [
        ("초기화 테스트", test_search_agent_initialization),
        ("하이브리드 검색 테스트", test_search_agent_hybrid_search),
        ("조항 번호 쿼리 테스트", test_search_agent_with_clause_number),
        ("빈 쿼리 테스트", test_search_agent_empty_query),
        ("여러 쿼리 연속 처리 테스트", test_search_agent_multiple_queries),
        ("토큰 제한 테스트", test_search_agent_token_limits),
        ("AnswerAgent 호환성 테스트", test_search_agent_state_compatibility),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            logger.info(f"\n[{test_name}]")
            asyncio.run(test_func())
            passed += 1
        except Exception as e:
            logger.error(f"❌ {test_name} 실패: {e}")
            failed += 1
    
    logger.info("\n" + "=" * 60)
    logger.info(f"테스트 결과: {passed}개 통과, {failed}개 실패")
    logger.info("=" * 60)
    
    if failed == 0:
        logger.info("✅ 모든 통합 테스트 통과!")
    else:
        logger.error(f"❌ {failed}개 테스트 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()

