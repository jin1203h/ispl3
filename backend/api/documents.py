"""
문서 관리 API
Management Agent 기반으로 리팩토링
"""
from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import FileResponse
from typing import Optional
import logging

from core.database import SessionDep
from agents.management_agent import management_agent
from agents.state import create_initial_state
from services.document_management import DocumentManagementService

router = APIRouter(prefix="/api/documents", tags=["Documents"])
logger = logging.getLogger(__name__)


@router.get("/")
async def list_documents(
    session: SessionDep,
    filename: Optional[str] = Query(None, description="파일명 필터 (부분 일치)"),
    document_type: Optional[str] = Query(None, description="문서 유형 필터"),
    company_name: Optional[str] = Query(None, description="회사명 필터 (부분 일치)"),
    status: str = Query('active', description="상태 필터"),
    sort_by: str = Query('created_at', pattern='^(created_at|filename)$', description="정렬 기준"),
    sort_order: str = Query('desc', pattern='^(asc|desc)$', description="정렬 순서"),
    offset: int = Query(0, ge=0, description="오프셋"),
    limit: int = Query(20, ge=1, le=100, description="제한")
):
    """
    등록된 문서 목록 조회 (Management Agent 기반)
    
    Args:
        filename: 파일명 필터 (부분 일치)
        document_type: 문서 유형 필터
        company_name: 회사명 필터 (부분 일치)
        status: 상태 필터
        sort_by: 정렬 기준 ('created_at' or 'filename')
        sort_order: 정렬 순서 ('asc' or 'desc')
        offset: 오프셋
        limit: 제한 (최대 100)
        
    Returns:
        문서 목록 및 메타데이터
    """
    try:
        # State 생성
        state = create_initial_state("")
        state["task_type"] = "manage"
        state["management_action"] = "list"
        state["filter_filename"] = filename
        state["filter_document_type"] = document_type
        state["filter_company_name"] = company_name
        state["sort_by"] = sort_by
        state["sort_order"] = sort_order
        state["offset"] = offset
        state["limit"] = limit
        
        # Management Agent 호출
        result = await management_agent.manage(state)
        
        if result.get("error"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error")
            )
        
        return result.get("management_result", {})
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 목록 조회 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 목록 조회 실패: {str(e)}"
        )


@router.get("/{document_id}")
async def get_document(document_id: int, session: SessionDep):
    """
    특정 문서 상세 조회 (Management Agent 기반)
    
    Args:
        document_id: 문서 ID
        
    Returns:
        문서 상세 정보
    """
    try:
        # State 생성
        state = create_initial_state("")
        state["task_type"] = "manage"
        state["management_action"] = "view"
        state["document_id"] = document_id
        
        # Management Agent 호출
        result = await management_agent.manage(state)
        
        if result.get("error"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("error")
            )
        
        # management_result에서 document 정보 추출
        management_result = result.get("management_result", {})
        if management_result.get("success"):
            return management_result.get("document", {})
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"문서를 찾을 수 없습니다: ID={document_id}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 조회 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 조회 실패: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(document_id: int, session: SessionDep):
    """
    문서 삭제 (Management Agent 기반)
    
    Args:
        document_id: 문서 ID
        
    Returns:
        삭제 결과
    """
    try:
        # State 생성
        state = create_initial_state("")
        state["task_type"] = "manage"
        state["management_action"] = "delete"
        state["document_id"] = document_id
        
        # Management Agent 호출
        result = await management_agent.manage(state)
        
        if result.get("error"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error")
            )
        
        return result.get("management_result", {})
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 삭제 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 삭제 실패: {str(e)}"
        )


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    session: SessionDep,
    file_type: str = Query('pdf', pattern='^(pdf|markdown)$', description="파일 유형"),
    inline: bool = Query(False, description="브라우저에서 열기 (true) vs 다운로드 (false)")
):
    """
    문서 다운로드 또는 표시 (PDF 또는 Markdown)
    
    Args:
        document_id: 문서 ID
        file_type: 파일 유형 ('pdf' or 'markdown')
        inline: True면 브라우저에서 열기, False면 다운로드
        
    Returns:
        파일 스트리밍
    """
    try:
        from urllib.parse import quote
        
        service = DocumentManagementService()
        file_path = await service.get_document_file_path(
            session=session,
            document_id=document_id,
            file_type=file_type
        )
        
        # 한글 파일명 처리 (UTF-8 인코딩)
        filename_encoded = quote(file_path.name)
        headers = {}
        if inline:
            # 브라우저에서 표시
            headers['Content-Disposition'] = f"inline; filename*=UTF-8''{filename_encoded}"
        else:
            # 다운로드
            headers['Content-Disposition'] = f"attachment; filename*=UTF-8''{filename_encoded}"
        
        return FileResponse(
            path=str(file_path),
            media_type='application/pdf' if file_type == 'pdf' else 'text/markdown',
            headers=headers
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 다운로드 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 다운로드 실패: {str(e)}"
        )


@router.get("/{document_id}/view")
async def view_document(
    document_id: int,
    session: SessionDep,
    file_type: str = Query('pdf', pattern='^(pdf|markdown)$', description="파일 유형")
):
    """
    문서 조회 (뷰어용)
    
    Args:
        document_id: 문서 ID
        file_type: 파일 유형 ('pdf' or 'markdown')
        
    Returns:
        Markdown의 경우 텍스트 내용, PDF의 경우 다운로드 URL
    """
    try:
        service = DocumentManagementService()
        content = await service.get_document_content(
            session=session,
            document_id=document_id,
            file_type=file_type
        )
        return content
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 조회 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 조회 실패: {str(e)}"
        )


@router.get("/health")
async def documents_health():
    """
    문서 API 상태 확인
    """
    return {
        "status": "ok",
        "service": "documents"
    }

