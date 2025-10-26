"""
Management Agent
문서 관리(조회, 삭제, 다운로드)를 담당하는 Agent
"""
import logging
from typing import Optional

from agents.state import ISPLState
from services.document_management import DocumentManagementService
from core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class ManagementAgent:
    """문서 관리를 담당하는 Agent"""
    
    def __init__(self):
        """Management Agent 초기화"""
        self.doc_service = DocumentManagementService()
        logger.info("ManagementAgent 초기화 완료")
    
    async def manage(self, state: ISPLState) -> dict:
        """
        문서 관리 작업을 수행합니다.
        
        지원하는 작업:
        - list: 문서 목록 조회
        - delete: 문서 삭제
        - view: 문서 조회
        
        Args:
            state: 현재 상태
        
        Returns:
            업데이트할 상태 딕셔너리
        """
        query = state.get("query", "")
        management_action = state.get("management_action", "list")
        document_id = state.get("document_id")
        
        session = AsyncSessionLocal()
        
        try:
            if management_action == "list" or "목록" in query:
                return await self._list_documents(session, state)
            
            elif management_action == "delete" or "삭제" in query:
                if document_id:
                    return await self._delete_document(session, document_id)
                else:
                    return {
                        "error": "삭제할 문서 ID가 필요합니다",
                        "final_answer": "삭제할 문서를 지정해주세요.",
                        "task_results": {
                            "management": {
                                "success": False,
                                "error": "document_id 필요"
                            }
                        }
                    }
            
            elif management_action == "view" or "조회" in query or "보기" in query:
                if document_id:
                    return await self._view_document(session, document_id)
                else:
                    # document_id가 없으면 목록 조회
                    return await self._list_documents(session, state)
            
            else:
                # 기본값: 목록 조회
                return await self._list_documents(session, state)
        
        finally:
            await session.close()
    
    async def _list_documents(
        self,
        session,
        state: ISPLState
    ) -> dict:
        """
        문서 목록을 조회합니다.
        
        Args:
            session: DB 세션
            state: 현재 상태
        
        Returns:
            문서 목록 및 응답
        """
        logger.info("문서 목록 조회 시작")
        
        # state에서 필터/정렬 옵션 추출
        filename = state.get("filter_filename")
        document_type = state.get("filter_document_type")
        company_name = state.get("filter_company_name")
        sort_by = state.get("sort_by", "created_at")
        sort_order = state.get("sort_order", "desc")
        offset = state.get("offset", 0)
        limit = state.get("limit", 20)
        
        result = await self.doc_service.list_documents(
            session=session,
            filename=filename,
            document_type=document_type,
            company_name=company_name,
            sort_by=sort_by,
            sort_order=sort_order,
            offset=offset,
            limit=limit
        )
        
        documents = result['documents']
        total = result['total']
        
        # 응답 메시지 생성
        if total == 0:
            answer = "등록된 약관이 없습니다."
        else:
            answer = f"**📋 등록된 약관 목록** (총 {total}개)\n\n"
            
            for idx, doc in enumerate(documents[:5], 1):  # 최대 5개만 표시
                answer += f"**{idx}. {doc['filename']}**\n"
                if doc['company_name']:
                    answer += f"   - 회사: {doc['company_name']}\n"
                answer += f"   - 페이지: {doc['total_pages'] or 'N/A'}, 청크: {doc['total_chunks']}개\n"
                answer += f"   - 등록일: {doc['created_at'][:10] if doc['created_at'] else 'N/A'}\n"
                answer += "\n"
            
            if total > 5:
                answer += f"\n...외 {total - 5}개 문서"
        
        return {
            "management_result": result,
            "final_answer": answer,
            "task_results": {
                "management": {
                    "success": True,
                    "action": "list",
                    "total": total
                }
            },
            "error": None
        }
    
    async def _delete_document(
        self,
        session,
        document_id: int
    ) -> dict:
        """
        문서를 삭제합니다.
        
        Args:
            session: DB 세션
            document_id: 문서 ID
        
        Returns:
            삭제 결과
        """
        logger.info(f"문서 삭제 시작: document_id={document_id}")
        
        try:
            result = await self.doc_service.delete_document(
                session=session,
                document_id=document_id
            )
            
            if result['success']:
                answer = (
                    f"✅ 문서가 삭제되었습니다.\n\n"
                    f"**파일명**: {result.get('filename', 'N/A')}\n"
                    f"**문서 ID**: {document_id}"
                )
                
                return {
                    "management_result": result,
                    "final_answer": answer,
                    "task_results": {
                        "management": {
                            "success": True,
                            "action": "delete",
                            "document_id": document_id
                        }
                    },
                    "error": None
                }
            else:
                error_msg = result.get('error', '알 수 없는 오류')
                
                return {
                    "error": error_msg,
                    "final_answer": f"❌ 문서 삭제 실패: {error_msg}",
                    "task_results": {
                        "management": {
                            "success": False,
                            "action": "delete",
                            "error": error_msg
                        }
                    }
                }
        
        except Exception as e:
            logger.error(f"문서 삭제 중 오류: {e}", exc_info=True)
            
            return {
                "error": str(e),
                "final_answer": f"❌ 문서 삭제 중 오류가 발생했습니다: {str(e)}",
                "task_results": {
                    "management": {
                        "success": False,
                        "action": "delete",
                        "error": str(e)
                    }
                }
            }
    
    async def _view_document(
        self,
        session,
        document_id: int
    ) -> dict:
        """
        문서 상세 정보를 조회합니다.
        
        Args:
            session: DB 세션
            document_id: 문서 ID
        
        Returns:
            문서 상세 정보
        """
        logger.info(f"문서 조회 시작: document_id={document_id}")
        
        try:
            result = await self.doc_service.get_document(
                session=session,
                document_id=document_id
            )
            
            if result['success']:
                doc = result['document']
                
                answer = (
                    f"**📄 문서 상세 정보**\n\n"
                    f"**파일명**: {doc['filename']}\n"
                    f"**문서 타입**: {doc.get('document_type', 'N/A')}\n"
                    f"**회사명**: {doc.get('company_name', 'N/A')}\n"
                    f"**페이지**: {doc.get('total_pages', 'N/A')}페이지\n"
                    f"**청크**: {doc.get('total_chunks', 0)}개\n"
                    f"**등록일**: {doc.get('created_at', 'N/A')}\n"
                    f"**상태**: {doc.get('status', 'N/A')}"
                )
                
                return {
                    "management_result": result,
                    "final_answer": answer,
                    "task_results": {
                        "management": {
                            "success": True,
                            "action": "view",
                            "document_id": document_id
                        }
                    },
                    "error": None
                }
            else:
                error_msg = result.get('error', '문서를 찾을 수 없습니다')
                
                return {
                    "error": error_msg,
                    "final_answer": f"❌ {error_msg}",
                    "task_results": {
                        "management": {
                            "success": False,
                            "action": "view",
                            "error": error_msg
                        }
                    }
                }
        
        except Exception as e:
            logger.error(f"문서 조회 중 오류: {e}", exc_info=True)
            
            return {
                "error": str(e),
                "final_answer": f"❌ 문서 조회 중 오류가 발생했습니다: {str(e)}",
                "task_results": {
                    "management": {
                        "success": False,
                        "action": "view",
                        "error": str(e)
                    }
                }
            }


# 전역 Management Agent 인스턴스
management_agent = ManagementAgent()


async def management_node(state: ISPLState) -> dict:
    """
    Management Agent 노드 함수
    
    Args:
        state: 현재 상태
    
    Returns:
        업데이트할 상태 딕셔너리
    """
    return await management_agent.manage(state)



