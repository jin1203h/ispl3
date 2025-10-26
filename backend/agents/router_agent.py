"""
Router Agent
사용자 요청을 분석하여 적절한 Agent로 라우팅합니다.
"""
import logging
from typing import Literal
from langgraph.types import Command

from agents.state import ISPLState

logger = logging.getLogger(__name__)


class RouterAgent:
    """사용자 요청을 분석하여 적절한 Agent로 라우팅하는 Agent"""
    
    # 의도 분류를 위한 키워드
    SEARCH_KEYWORDS = [
        "검색", "찾아", "알려줘", "알려주세요", "무엇", "어떻게", "언제",
        "보장", "보험", "약관", "조항", "내용", "설명", "궁금",
        "질문", "문의", "확인", "가입", "해지", "청구"
    ]
    
    UPLOAD_KEYWORDS = [
        "업로드", "올려", "등록", "추가", "파일", "PDF", "문서"
    ]
    
    MANAGE_KEYWORDS = [
        "관리", "목록", "삭제", "다운로드", "조회", "보기"
    ]
    
    def __init__(self):
        """Router Agent 초기화"""
        logger.info("RouterAgent 초기화 완료")
    
    def classify_intent(self, query: str) -> Literal["search", "upload", "manage"]:
        """
        사용자 질의에서 의도를 분류합니다.
        
        Args:
            query: 사용자 질의
        
        Returns:
            의도 유형 (search/upload/manage)
        """
        query_lower = query.lower()
        
        # 키워드 매칭으로 의도 분류
        upload_score = sum(1 for keyword in self.UPLOAD_KEYWORDS if keyword in query_lower)
        manage_score = sum(1 for keyword in self.MANAGE_KEYWORDS if keyword in query_lower)
        search_score = sum(1 for keyword in self.SEARCH_KEYWORDS if keyword in query_lower)
        
        # 점수가 가장 높은 의도 선택
        scores = {
            "upload": upload_score,
            "manage": manage_score,
            "search": search_score
        }
        
        intent = max(scores, key=scores.get)
        
        # 모든 점수가 0이면 기본값은 search
        if scores[intent] == 0:
            intent = "search"
        
        logger.info(f"의도 분류: '{query[:50]}...' → {intent} (점수: {scores})")
        return intent
    
    def route(self, state: ISPLState) -> Command[Literal["search_agent", "processing_agent", "management_agent"]]:
        """
        상태를 분석하여 다음 Agent를 결정합니다.
        
        Args:
            state: 현재 상태
        
        Returns:
            Command: 다음 Agent 명령
        """
        query = state.get("query", "")
        
        # task_type이 명시적으로 지정된 경우 우선 사용
        task_type = state.get("task_type")
        
        if task_type:
            # 명시적 task_type이 있는 경우
            intent = task_type
            logger.info(f"명시적 task_type 사용: {intent}")
        else:
            # 빈 쿼리는 search로 처리
            if not query:
                logger.warning("질의가 비어있습니다. search_agent에서 처리합니다.")
                intent = "search"
            else:
                # 의도 분류
                intent = self.classify_intent(query)
        
        # Agent 선택
        if intent == "search":
            next_agent = "search_agent"
        elif intent == "upload":
            next_agent = "processing_agent"
        elif intent == "manage":
            next_agent = "management_agent"
        else:
            # 기본값: search
            logger.warning(f"알 수 없는 intent '{intent}', search로 대체합니다.")
            intent = "search"
            next_agent = "search_agent"
        
        logger.info(f"라우팅: {intent} → {next_agent}")
        
        return Command(
            goto=next_agent,
            update={
                "task_type": intent,
                "next_agent": next_agent
            }
        )


# 전역 Router Agent 인스턴스
router_agent = RouterAgent()


def router_node(state: ISPLState) -> Command[Literal["search_agent", "processing_agent", "management_agent"]]:
    """
    Router Agent 노드 함수
    
    Args:
        state: 현재 상태
    
    Returns:
        Command: 다음 노드로의 라우팅 명령
    """
    return router_agent.route(state)

