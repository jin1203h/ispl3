"""
Chunk Expansion Agent
컨텍스트 확장을 실행하는 Agent입니다.
"""
import logging
from typing import List, Dict, Any

from agents.state import ISPLState
from services.chunk_expansion_service import ChunkExpansionService
from services.vector_search import VectorSearchResult
from core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class ChunkExpansionAgent:
    """
    청크 확장 Agent
    
    Context Judgement Agent의 판단에 따라
    지정된 청크들을 확장합니다.
    """
    
    def __init__(self):
        """Chunk Expansion Agent 초기화"""
        self.expansion_service = ChunkExpansionService()
        logger.info("ChunkExpansionAgent 초기화 완료")
    
    async def expand(self, state: ISPLState) -> dict:
        """
        청크 확장을 실행합니다.
        
        Args:
            state: 현재 상태
        
        Returns:
            업데이트할 상태 딕셔너리
        """
        search_results = state.get("search_results", [])
        chunks_to_expand = state.get("chunks_to_expand", [])  # ⭐ 이제 딕셔너리 리스트
        expansion_count = state.get("expansion_count", 0)
        
        logger.info(
            f"청크 확장 시작: "
            f"total_chunks={len(search_results)}, "
            f"to_expand={len(chunks_to_expand)}, "
            f"count={expansion_count}"
        )
        
        # 확장할 청크가 없는 경우
        if not chunks_to_expand:
            logger.warning("확장할 청크가 지정되지 않았습니다.")
            return {
                "expansion_count": expansion_count + 1,
                "task_results": {
                    "chunk_expansion": {
                        "success": True,
                        "expanded": False,
                        "reason": "확장할 청크 없음"
                    }
                },
                "next_agent": "context_judgement_agent"  # 다시 판단
            }
        
        try:
            # 데이터베이스 세션 생성
            session = AsyncSessionLocal()
            
            try:
                # VectorSearchResult 객체로 변환
                search_result_objects = []
                for result in search_results:
                    search_result_objects.append(
                        VectorSearchResult(
                            chunk_id=result["chunk_id"],
                            document_id=result["document_id"],
                            content=result["content"],
                            similarity=result["similarity"],
                            chunk_type=result["chunk_type"],
                            page_number=result.get("page_number"),
                            section_title=result.get("section_title"),
                            clause_number=result.get("clause_number"),
                            metadata=result.get("metadata", {}),
                            document_filename=result.get("document", {}).get("filename"),
                            document_type=result.get("document", {}).get("type"),
                            company_name=result.get("document", {}).get("company_name")
                        )
                    )
                
                # 청크 확장 실행 (방향 정보 포함)
                expanded_results = await self.expansion_service.expand_search_results(
                    session=session,
                    search_results=search_result_objects,
                    chunks_to_expand=chunks_to_expand,  # ⭐ 딕셔너리 리스트 전달
                    max_tokens=15000  # gpt-4o 변경으로 6000 → 15000 증가
                )
                
                # 딕셔너리로 변환
                expanded_dicts = [result.to_dict() for result in expanded_results]
                
                # 확장된 청크 ID 수집
                expanded_chunk_ids = []
                for result in expanded_results:
                    if result.metadata.get("expanded", False):
                        expanded_chunk_ids.append(result.chunk_id)
                
                logger.info(
                    f"청크 확장 완료: "
                    f"expanded_count={len(expanded_chunk_ids)}"
                )
                
                # ⭐ 디버그: 확장된 결과 검증
                for idx, result_dict in enumerate(expanded_dicts):
                    metadata = result_dict.get("metadata", {})
                    is_expanded = metadata.get("expanded", False)
                    included = metadata.get("included_chunks", [])
                    logger.info(
                        f"  확장 결과[{idx}]: chunk_id={result_dict['chunk_id']}, "
                        f"expanded={is_expanded}, included_chunks={included}"
                    )
                
                return_value = {
                    "search_results": expanded_dicts,  # 확장된 결과로 업데이트
                    "expanded_chunks": expanded_chunk_ids,
                    "expansion_count": expansion_count + 1,
                    "chunks_to_expand": [],  # 초기화
                    "task_results": {
                        "chunk_expansion": {
                            "success": True,
                            "expanded": True,
                            "expanded_chunk_ids": expanded_chunk_ids,
                            "expansion_count": expansion_count + 1
                        }
                    },
                    "next_agent": "context_judgement_agent"  # 다시 판단
                }
                
                logger.info(
                    f"⭐ 반환값: search_results 개수={len(return_value['search_results'])}"
                )
                logger.info(
                    f"⭐ search_results의 chunk_id들: {[r['chunk_id'] for r in return_value['search_results']]}"
                )
                
                return return_value
            
            finally:
                # 세션 정리
                await session.close()
        
        except Exception as e:
            logger.error(f"청크 확장 중 오류 발생: {e}", exc_info=True)
            return {
                "error": f"청크 확장 중 오류: {str(e)}",
                "expansion_count": expansion_count + 1,
                "task_results": {
                    "chunk_expansion": {
                        "success": False,
                        "error": str(e)
                    }
                },
                "next_agent": "answer_agent"  # 오류 시 답변 생성으로
            }


# 전역 Chunk Expansion Agent 인스턴스
chunk_expansion_agent = ChunkExpansionAgent()


async def chunk_expansion_node(state: ISPLState) -> dict:
    """
    Chunk Expansion Agent 노드 함수
    
    Args:
        state: 현재 상태
    
    Returns:
        업데이트할 상태 딕셔너리
    """
    return await chunk_expansion_agent.expand(state)

