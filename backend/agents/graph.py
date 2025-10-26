"""
ISPL LangGraph StateGraph 구성
Multi-Agent 시스템의 워크플로우를 정의합니다.
"""
import logging
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.state import ISPLState
from agents.router_agent import router_node
from agents.search_agent import search_node
from agents.context_judgement_agent import context_judgement_node
from agents.chunk_expansion_agent import chunk_expansion_node
from agents.answer_agent import answer_node
from agents.processing_agent import processing_node
from agents.management_agent import management_node

logger = logging.getLogger(__name__)


def create_graph() -> StateGraph:
    """
    ISPL LangGraph를 생성합니다.
    
    Returns:
        컴파일된 StateGraph
    """
    logger.info("ISPL LangGraph 생성 시작")
    
    # StateGraph 초기화
    builder = StateGraph(ISPLState)
    
    # 노드 추가
    builder.add_node("router", router_node)
    builder.add_node("search_agent", search_node)
    builder.add_node("context_judgement_agent", context_judgement_node)
    builder.add_node("chunk_expansion_agent", chunk_expansion_node)
    builder.add_node("answer_agent", answer_node)
    builder.add_node("processing_agent", processing_node)
    builder.add_node("management_agent", management_node)
    
    # 시작 엣지: START → router
    builder.add_edge(START, "router")
    
    # router에서 조건부 라우팅
    # Command 객체가 자동으로 다음과 같이 라우팅:
    # - task_type="search" → search_agent
    # - task_type="upload" → processing_agent
    # - task_type="manage" → management_agent
    
    # search_agent → context_judgement_agent (컨텍스트 판단)
    builder.add_edge("search_agent", "context_judgement_agent")
    
    # context_judgement_agent에서 조건부 라우팅
    # - 충분함 (context_sufficient=True) → answer_agent
    # - 불충분함 (context_sufficient=False) → chunk_expansion_agent
    def route_after_judgement(state: ISPLState) -> str:
        """컨텍스트 판단 후 라우팅"""
        is_sufficient = state.get("context_sufficient", True)
        if is_sufficient:
            logger.debug("컨텍스트 충분 → answer_agent")
            return "answer_agent"
        else:
            logger.debug("컨텍스트 불충분 → chunk_expansion_agent")
            return "chunk_expansion_agent"
    
    builder.add_conditional_edges(
        "context_judgement_agent",
        route_after_judgement,
        {
            "answer_agent": "answer_agent",
            "chunk_expansion_agent": "chunk_expansion_agent"
        }
    )
    
    # chunk_expansion_agent → context_judgement_agent (재판단)
    builder.add_edge("chunk_expansion_agent", "context_judgement_agent")
    
    # answer_agent → END
    builder.add_edge("answer_agent", END)
    
    # processing_agent → END (처리 완료 후 바로 종료)
    builder.add_edge("processing_agent", END)
    
    # management_agent → END (관리 작업 완료 후 바로 종료)
    builder.add_edge("management_agent", END)
    
    # 메모리 체크포인트 (대화 이력 저장용)
    memory = MemorySaver()
    
    # 그래프 컴파일
    graph = builder.compile(checkpointer=memory)
    
    logger.info("ISPL LangGraph 생성 완료")
    
    return graph


# 전역 그래프 인스턴스 (지연 생성)
_ispl_graph = None


def get_graph() -> StateGraph:
    """
    그래프 인스턴스를 반환합니다 (지연 생성).
    매번 호출 시 새로운 그래프를 반환하여 이벤트 루프 문제를 방지합니다.
    
    Returns:
        컴파일된 StateGraph
    """
    # 매번 새로 생성하여 이벤트 루프 문제 해결
    return create_graph()


# 하위 호환성을 위한 별칭
ispl_graph = property(lambda self: get_graph())


async def run_graph(query: str, thread_id: str = "default") -> dict:
    """
    그래프를 실행하고 결과를 반환합니다.
    
    Args:
        query: 사용자 질의
        thread_id: 대화 스레드 ID (대화 이력 관리용)
    
    Returns:
        최종 상태 딕셔너리
    """
    logger.info(f"그래프 실행 시작: query='{query[:50]}...', thread={thread_id}")
    
    # 초기 상태 설정
    initial_state = {
        "query": query,
        "messages": [],
        "next_agent": "router",
        "task_type": "search",
        "task_results": {},
        "search_results": [],
        "final_answer": "",
        "error": None,
        "context_sufficient": None,
        "expanded_chunks": [],
        "expansion_count": 0,
        "chunks_to_expand": []
    }
    
    # 설정 (스레드 ID 포함)
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        # 그래프 생성 및 실행
        graph = get_graph()
        final_state = await graph.ainvoke(initial_state, config)
        
        logger.info(f"그래프 실행 완료: answer_length={len(final_state.get('final_answer', ''))}")
        
        return final_state
    
    except Exception as e:
        logger.error(f"그래프 실행 중 오류 발생: {e}", exc_info=True)
        return {
            "query": query,
            "final_answer": f"시스템 오류가 발생했습니다: {str(e)}",
            "error": str(e),
            "task_results": {
                "system": {
                    "success": False,
                    "error": str(e)
                }
            }
        }


async def stream_graph(query: str, thread_id: str = "default"):
    """
    그래프를 스트리밍 방식으로 실행합니다.
    
    Args:
        query: 사용자 질의
        thread_id: 대화 스레드 ID
    
    Yields:
        각 노드의 실행 결과
    """
    logger.info(f"그래프 스트리밍 시작: query='{query[:50]}...'")
    
    # 초기 상태 설정
    initial_state = {
        "query": query,
        "messages": [],
        "next_agent": "router",
        "task_type": "search",
        "task_results": {},
        "search_results": [],
        "final_answer": "",
        "error": None,
        "context_sufficient": None,
        "expanded_chunks": [],
        "expansion_count": 0,
        "chunks_to_expand": []
    }
    
    # 설정
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        # 그래프 생성 및 스트리밍 실행
        graph = get_graph()
        async for event in graph.astream(initial_state, config):
            logger.debug(f"스트리밍 이벤트: {list(event.keys())}")
            yield event
    
    except Exception as e:
        logger.error(f"그래프 스트리밍 중 오류 발생: {e}", exc_info=True)
        yield {
            "error": {
                "error": str(e),
                "final_answer": f"시스템 오류가 발생했습니다: {str(e)}"
            }
        }

