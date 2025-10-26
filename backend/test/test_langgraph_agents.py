"""
LangGraph Agent 테스트
Router, Search, Answer Agent와 StateGraph의 동작을 테스트합니다.
"""
import sys
import os
from pathlib import Path

# 테스트 환경 설정 (모듈 import 전에 설정)
os.environ["TESTING"] = "true"

# backend 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import asyncio
import logging

from agents.router_agent import router_agent
from agents.graph import run_graph

# DEBUG 레벨로 변경하여 상세 로그 확인
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# 특정 모듈만 DEBUG로 설정
logging.getLogger('agents.search_agent').setLevel(logging.DEBUG)
logging.getLogger('services.vector_search').setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


async def test_router_agent():
    """Router Agent 의도 분류 테스트"""
    logger.info("=" * 80)
    logger.info("Router Agent 의도 분류 테스트")
    logger.info("=" * 80)
    
    test_queries = [
        ("골절 시 보장 여부는 어떻게 되나요?", "search"),
        ("보험료 납입 방법에 대해 알려주세요", "search"),
        ("파일 업로드하고 싶어요", "upload"),
        ("PDF 등록 방법", "upload"),
        ("약관 목록 보여줘", "manage"),
        ("삭제하고 싶어요", "manage"),
    ]
    
    for query, expected_intent in test_queries:
        intent = router_agent.classify_intent(query)
        status = "✅" if intent == expected_intent else "❌"
        logger.info(f"{status} '{query}' → {intent} (기대: {expected_intent})")
    
    logger.info("\n✅ Router Agent 테스트 완료\n")


async def test_full_graph():
    """전체 LangGraph 워크플로우 테스트"""
    logger.info("=" * 80)
    logger.info("LangGraph 전체 워크플로우 테스트")
    logger.info("=" * 80)
    
    test_queries = [
        "골절 시 보장 여부는 어떻게 되나요?",
        "보험료는 어떻게 납입하나요?",
        "계약 해지 시 환급금에 대해 알려주세요"
    ]
    
    for idx, query in enumerate(test_queries, 1):
        logger.info(f"\n{'=' * 80}")
        logger.info(f"테스트 {idx}/{len(test_queries)}: {query}")
        logger.info(f"{'=' * 80}")
        
        try:
            # LangGraph 실행
            final_state = await run_graph(
                query=query,
                thread_id=f"test_{idx}"
            )
            
            # 결과 확인
            final_answer = final_state.get("final_answer", "")
            search_results = final_state.get("search_results", [])
            task_results = final_state.get("task_results", {})
            error = final_state.get("error")
            
            if error:
                logger.error(f"❌ 오류 발생: {error}")
            else:
                logger.info(f"\n✅ 답변 생성 성공")
                logger.info(f"검색 결과: {len(search_results)}개")
                logger.info(f"답변 길이: {len(final_answer)}자")
                logger.info(f"\n📝 답변:")
                logger.info(f"{final_answer}\n")
                
                # 작업 결과 확인
                if "search" in task_results:
                    search_info = task_results["search"]
                    logger.info(f"검색 성공: {search_info.get('success')}")
                    logger.info(f"검색된 청크 수: {search_info.get('count')}")
                
                if "answer" in task_results:
                    answer_info = task_results["answer"]
                    logger.info(f"답변 생성 성공: {answer_info.get('success')}")
                    if "tokens_used" in answer_info:
                        logger.info(f"사용된 토큰: {answer_info.get('tokens_used')}")
        
        except Exception as e:
            logger.error(f"❌ 테스트 실패: {e}", exc_info=True)
        
        # API 응답 시간 고려하여 잠시 대기
        await asyncio.sleep(2)
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ LangGraph 전체 테스트 완료")
    logger.info("=" * 80)


async def test_graph_state_flow():
    """StateGraph 상태 흐름 테스트"""
    logger.info("=" * 80)
    logger.info("StateGraph 상태 흐름 테스트")
    logger.info("=" * 80)
    
    query = "보험금 청구 절차를 알려주세요"
    
    logger.info(f"\n질의: {query}")
    logger.info("\n예상 흐름:")
    logger.info("START → router → search_agent → answer_agent → END")
    
    try:
        final_state = await run_graph(query=query, thread_id="state_flow_test")
        
        logger.info("\n✅ 그래프 실행 완료")
        logger.info(f"최종 상태:")
        logger.info(f"  - task_type: {final_state.get('task_type')}")
        logger.info(f"  - 검색 결과 수: {len(final_state.get('search_results', []))}")
        logger.info(f"  - 답변 생성 여부: {'final_answer' in final_state and bool(final_state.get('final_answer'))}")
        logger.info(f"  - 오류 여부: {final_state.get('error')}")
        
    except Exception as e:
        logger.error(f"❌ 상태 흐름 테스트 실패: {e}", exc_info=True)
    
    logger.info("\n✅ StateGraph 상태 흐름 테스트 완료\n")


if __name__ == "__main__":
    # Router Agent 테스트
    asyncio.run(test_router_agent())
    
    # StateGraph 상태 흐름 테스트
    asyncio.run(test_graph_state_flow())
    
    # 전체 워크플로우 테스트
    asyncio.run(test_full_graph())

