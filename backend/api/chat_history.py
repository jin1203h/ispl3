"""
대화 이력 API
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

from core.database import SessionDep
from services.chat_history import ChatHistoryService

router = APIRouter(prefix="/api/chat/history", tags=["Chat History"])
logger = logging.getLogger(__name__)


# Request/Response 모델
class MessageSaveRequest(BaseModel):
    """메시지 저장 요청"""
    thread_id: str = Field(..., description="스레드 ID")
    role: str = Field(..., description="역할 (user/assistant/system)")
    content: str = Field(..., description="메시지 내용")
    message_metadata: Optional[Dict[str, Any]] = Field(None, description="메타데이터")


class SessionUpdateRequest(BaseModel):
    """세션 업데이트 요청"""
    title: str = Field(..., description="새 제목")


class MessageResponse(BaseModel):
    """메시지 응답"""
    id: int
    role: str
    content: str
    message_metadata: Optional[Dict[str, Any]]
    created_at: str


class SessionResponse(BaseModel):
    """세션 응답"""
    id: int
    thread_id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str


@router.post("/messages", status_code=201)
async def save_message(
    request: MessageSaveRequest,
    session: SessionDep
):
    """
    메시지를 저장합니다.
    
    Args:
        request: 메시지 저장 요청
        session: DB 세션
    
    Returns:
        저장된 메시지 정보
    """
    try:
        service = ChatHistoryService()
        message = await service.save_message(
            session=session,
            thread_id=request.thread_id,
            role=request.role,
            content=request.content,
            message_metadata=request.message_metadata
        )
        
        return {
            "success": True,
            "message": {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "message_metadata": message.message_metadata,
                "created_at": message.created_at.isoformat()
            }
        }
    
    except Exception as e:
        logger.error(f"메시지 저장 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{thread_id}/messages")
async def get_messages(
    thread_id: str,
    session: SessionDep,
    limit: Optional[int] = Query(None, description="제한 (최근 N개)")
):
    """
    세션의 메시지 목록을 조회합니다.
    
    Args:
        thread_id: 스레드 ID
        session: DB 세션
        limit: 제한
    
    Returns:
        메시지 목록
    """
    try:
        service = ChatHistoryService()
        messages = await service.get_session_messages(
            session=session,
            thread_id=thread_id,
            limit=limit
        )
        
        return {
            "success": True,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "message_metadata": msg.message_metadata,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in messages
            ]
        }
    
    except Exception as e:
        logger.error(f"메시지 조회 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_sessions(
    session: SessionDep,
    user_id: Optional[int] = Query(None, description="사용자 ID"),
    limit: int = Query(20, ge=1, le=100, description="제한"),
    offset: int = Query(0, ge=0, description="오프셋")
):
    """
    세션 목록을 조회합니다.
    
    Args:
        session: DB 세션
        user_id: 사용자 ID
        limit: 제한
        offset: 오프셋
    
    Returns:
        세션 목록
    """
    try:
        service = ChatHistoryService()
        result = await service.list_sessions(
            session=session,
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            **result
        }
    
    except Exception as e:
        logger.error(f"세션 목록 조회 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sessions/{thread_id}")
async def update_session(
    thread_id: str,
    request: SessionUpdateRequest,
    session: SessionDep
):
    """
    세션 제목을 업데이트합니다.
    
    Args:
        thread_id: 스레드 ID
        request: 업데이트 요청
        session: DB 세션
    
    Returns:
        성공 여부
    """
    try:
        service = ChatHistoryService()
        success = await service.update_session_title(
            session=session,
            thread_id=thread_id,
            title=request.title
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        return {"success": True, "message": "제목이 업데이트되었습니다"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 업데이트 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{thread_id}")
async def delete_session(
    thread_id: str,
    session: SessionDep
):
    """
    세션을 삭제합니다.
    
    Args:
        thread_id: 스레드 ID
        session: DB 세션
    
    Returns:
        성공 여부
    """
    try:
        service = ChatHistoryService()
        success = await service.delete_session(
            session=session,
            thread_id=thread_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        return {"success": True, "message": "세션이 삭제되었습니다"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 삭제 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def history_health():
    """
    대화 이력 API 상태 확인
    """
    return {
        "status": "ok",
        "service": "chat_history"
    }



