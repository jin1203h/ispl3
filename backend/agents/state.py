"""
ISPL Agent State 정의
LangGraph에서 사용하는 전역 상태를 정의합니다.
"""
from typing import TypedDict, Annotated, Literal, Optional
from langgraph.graph import MessagesState


def merge_dicts(left: dict, right: dict) -> dict:
    """
    두 딕셔너리를 병합하는 reducer 함수
    
    Args:
        left: 기존 딕셔너리
        right: 새로운 딕셔너리
    
    Returns:
        병합된 딕셔너리
    """
    result = left.copy() if left else {}
    if right:
        result.update(right)
    return result


class ISPLState(MessagesState):
    """
    ISPL Agent 시스템의 전역 상태
    
    MessagesState를 상속하여 메시지 이력을 자동으로 관리하고,
    추가적인 작업 상태 정보를 포함합니다.
    """
    # 다음에 실행할 Agent
    next_agent: str
    
    # 작업 유형: 'search', 'upload', 'manage'
    task_type: Literal["search", "upload", "manage"]
    
    # 각 Agent의 작업 결과 (merge_dicts로 병합)
    task_results: Annotated[dict, merge_dicts]
    
    # 검색 쿼리
    query: str
    
    # 검색 결과 (Search Agent에서 저장)
    search_results: list
    
    # 최종 답변 (Answer Agent에서 저장)
    final_answer: str
    
    # 오류 정보
    error: str | None
    
    # ===== Context Judgement Agent 관련 필드 =====
    # 컨텍스트 충분성 플래그
    context_sufficient: Optional[bool]
    
    # 확장된 청크 목록
    expanded_chunks: list
    
    # 확장 시도 횟수 (무한 루프 방지)
    expansion_count: int
    
    # 확장이 필요한 청크 ID 목록
    chunks_to_expand: list
    
    # ===== Processing Agent 관련 필드 =====
    # 업로드할 파일 데이터
    file_data: Optional[bytes]
    
    # 파일명
    filename: Optional[str]
    
    # PDF 처리 방식 ('pymupdf', 'vision', 'both')
    processing_method: Optional[str]
    
    # 문서 타입 ('policy', 'terms', 'guide')
    document_type: Optional[str]
    
    # 보험 타입
    insurance_type: Optional[str]
    
    # 보험사명
    company_name: Optional[str]
    
    # 처리 결과 (Processing Agent의 반환값)
    processing_result: Annotated[dict, merge_dicts]
    
    # ===== Management Agent 관련 필드 =====
    # 관리 작업 타입 ('list', 'delete', 'view')
    management_action: Optional[str]
    
    # 관리 작업 결과
    management_result: Annotated[dict, merge_dicts]
    
    # 대상 문서 ID
    document_id: Optional[int]
    
    # 목록 조회 필터
    filter_filename: Optional[str]
    filter_document_type: Optional[str]
    filter_company_name: Optional[str]
    
    # 목록 정렬 옵션
    sort_by: Optional[str]
    sort_order: Optional[str]
    
    # 페이지네이션
    offset: Optional[int]
    limit: Optional[int]


def create_initial_state(query: str, task_type: str = "search") -> ISPLState:
    """
    초기 상태를 생성합니다.
    
    Args:
        query: 사용자 질의
        task_type: 작업 유형 (기본: search)
    
    Returns:
        ISPLState: 초기화된 상태
    """
    return ISPLState(
        messages=[],
        next_agent="router",
        task_type=task_type,
        task_results={},
        query=query,
        search_results=[],
        final_answer="",
        error=None,
        # Context Judgement Agent 필드 초기화
        context_sufficient=None,
        expanded_chunks=[],
        expansion_count=0,
        chunks_to_expand=[],
        # Processing Agent 필드 초기화
        file_data=None,
        filename=None,
        processing_method="pymupdf",
        document_type="policy",
        insurance_type=None,
        company_name=None,
        processing_result={},
        # Management Agent 필드 초기화
        management_action="list",
        management_result={},
        document_id=None,
        filter_filename=None,
        filter_document_type=None,
        filter_company_name=None,
        sort_by="created_at",
        sort_order="desc",
        offset=0,
        limit=20
    )

