"""
Search Agent
하이브리드 검색(벡터 + 키워드)을 수행하고 결과를 상태에 저장합니다.
질의 전처리를 통해 검색 정확도를 향상시킵니다.
Re-ranking을 통해 정확한 매칭을 상위로 올립니다.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from agents.state import ISPLState
from services.vector_search import VectorSearchService
from services.hybrid_search import HybridSearchService
from services.query_preprocessor import QueryPreprocessor
from services.reranker import reranker_service  # ⭐ Re-ranker 추가
from models.preprocessed_query import PreprocessedQuery
from core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class SearchAgent:
    """하이브리드 검색(벡터 + 키워드)을 수행하는 Agent"""
    
    def __init__(self):
        """Search Agent 초기화"""
        self.vector_search_service = VectorSearchService()  # fallback 용도로 유지
        self.hybrid_search_service = HybridSearchService()  # 기본 검색
        self.query_preprocessor = QueryPreprocessor()  # 질의 전처리
        logger.info("SearchAgent 초기화 완료 (HybridSearchService + QueryPreprocessor)")
    
    async def search(self, state: ISPLState) -> dict:
        """
        하이브리드 검색(벡터 + 키워드)을 수행하고 결과를 반환합니다.
        
        질의 전처리를 통해 정규화, 표준화, 동의어 확장, 조항 번호 추출,
        불완전 질의 감지를 수행합니다.
        
        Args:
            state: 현재 상태
        
        Returns:
            업데이트할 상태 딕셔너리
        """
        query = state.get("query", "")
        
        if not query:
            logger.warning("검색 쿼리가 비어있습니다.")
            return {
                "error": "검색 쿼리가 비어있습니다.",
                "search_results": [],
                "next_agent": "answer_agent"
            }
        
        logger.info(f"하이브리드 검색 시작 (전처리 포함): '{query[:50]}...'")
        
        # 질의 전처리
        preprocessed = await self.query_preprocessor.preprocess(query)
        
        # 불완전 질의 처리
        if not preprocessed.is_complete:
            logger.info(f"불완전 질의 감지: {preprocessed.suggestions}")
            return {
                "error": None,
                "search_results": [],
                "suggestions": preprocessed.suggestions,
                "task_results": {
                    "search": {
                        "success": False,
                        "incomplete_query": True,
                        "suggestions": preprocessed.suggestions
                    }
                },
                "next_agent": "answer_agent"
            }
        
        # 동적 threshold 조정 (조항 번호 기반)
        threshold = 0.3 if preprocessed.clause_number else 0.7
        
        if preprocessed.clause_number:
            logger.info(
                f"📋 조항 번호 필터 적용: {preprocessed.clause_number}, "
                f"threshold 조정: 0.7 → {threshold}"
            )
        
        try:
            # 데이터베이스 세션 생성
            logger.debug("AsyncSessionLocal 생성 중...")
            session = AsyncSessionLocal()
            
            try:
                # 표준화된 쿼리로 하이브리드 검색 수행 (벡터 + 키워드)
                logger.debug("하이브리드 검색 서비스 호출 중...")
                results, total_tokens = await self.hybrid_search_service.hybrid_search(
                    session=session,
                    query=preprocessed.standardized,  # 표준화된 쿼리 사용
                    limit=5,
                    max_tokens=20000,  # gpt-4o 변경으로 8000 → 20000 증가
                    threshold=threshold,  # 동적 threshold
                    clause_number=preprocessed.clause_number,  # 추출된 조항 번호
                    user_id=None  # 추후 사용자 인증 추가 시 사용
                )
                
                # 검색 결과를 딕셔너리로 변환
                search_results = [result.to_dict() for result in results]
                
                # ⭐ Re-ranking 적용 (정확한 매칭을 상위로)
                if search_results and len(search_results) > 1:
                    logger.info(f"Re-ranking 적용 전: {len(search_results)}개 결과")
                    search_results = reranker_service.rerank(
                        query=query,  # 원본 질의 사용
                        search_results=search_results,
                        keywords=preprocessed.expanded_terms  # 전처리된 키워드 사용
                    )
                    logger.info(f"Re-ranking 적용 완료: {len(search_results)}개 결과 재정렬")
                
                logger.info(
                    f"하이브리드 검색 완료: {len(results)}개 결과, "
                    f"{total_tokens}토큰"
                )
                
                return {
                    "search_results": search_results,
                    "task_results": {
                        "search": {
                            "success": True,
                            "count": len(results),
                            "query": query,
                            "total_tokens": total_tokens,
                            "search_type": "hybrid",
                            "preprocessing": {
                                "original_query": preprocessed.original,
                                "standardized_query": preprocessed.standardized,
                                "clause_number": preprocessed.clause_number,
                                "expanded_terms": preprocessed.expanded_terms  # ⭐ 리스트 전체 저장
                            }
                        }
                    },
                    "next_agent": "answer_agent",
                    "error": None
                }
            
            finally:
                # 세션 정리
                await session.close()
                logger.debug("세션 종료 완료")
        
        except Exception as e:
            logger.error(f"하이브리드 검색 중 오류 발생: {e}", exc_info=True)
            logger.error(f"오류 타입: {type(e).__name__}")
            logger.error(f"오류 세부사항: {str(e)}")
            return {
                "error": f"검색 중 오류가 발생했습니다: {str(e)}",
                "search_results": [],
                "task_results": {
                    "search": {
                        "success": False,
                        "error": str(e)
                    }
                },
                "next_agent": "answer_agent"
            }


# 전역 Search Agent 인스턴스
search_agent = SearchAgent()


async def search_node(state: ISPLState) -> dict:
    """
    Search Agent 노드 함수
    
    Args:
        state: 현재 상태
    
    Returns:
        업데이트할 상태 딕셔너리
    """
    return await search_agent.search(state)
