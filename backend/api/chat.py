"""
채팅 API 엔드포인트
LangGraph Agent 시스템과 통합된 채팅 기능을 제공합니다.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json

from agents.graph import run_graph, stream_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    query: str = Field(..., min_length=1, description="사용자 질의")
    thread_id: Optional[str] = Field("default", description="대화 스레드 ID")
    stream: bool = Field(False, description="스트리밍 여부")


class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    query: str
    answer: str
    search_results: list = []
    task_results: dict = {}
    error: Optional[str] = None


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    채팅 메시지를 처리하고 답변을 반환합니다.
    
    - **query**: 사용자 질의 (필수)
    - **thread_id**: 대화 스레드 ID (선택, 기본: default)
    - **stream**: 스트리밍 여부 (선택, 기본: false)
    
    Returns:
        답변 및 검색 결과
    """
    logger.info(f"채팅 요청: query='{request.query[:50]}...', thread={request.thread_id}")
    
    try:
        # 스트리밍이 아닌 경우
        if not request.stream:
            # LangGraph 실행
            final_state = await run_graph(
                query=request.query,
                thread_id=request.thread_id
            )
            
            # 응답 생성
            response = ChatResponse(
                query=request.query,
                answer=final_state.get("final_answer", ""),
                search_results=final_state.get("search_results", []),
                task_results=final_state.get("task_results", {}),
                error=final_state.get("error")
            )
            
            logger.info(f"채팅 응답 생성 완료: answer_length={len(response.answer)}")
            return response
        
        else:
            # 스트리밍은 별도 엔드포인트 사용
            raise HTTPException(
                status_code=400,
                detail="스트리밍은 /api/chat/stream 엔드포인트를 사용하세요."
            )
    
    except Exception as e:
        logger.error(f"채팅 처리 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"채팅 처리 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    채팅 메시지를 스트리밍 방식으로 처리합니다.
    
    - **query**: 사용자 질의 (필수)
    - **thread_id**: 대화 스레드 ID (선택, 기본: default)
    
    Returns:
        Server-Sent Events 스트림
    """
    logger.info(f"채팅 스트리밍 요청: query='{request.query[:50]}...'")
    
    async def event_generator():
        """SSE 이벤트 생성기"""
        try:
            async for event in stream_graph(request.query, request.thread_id):
                # 각 노드의 실행 결과를 SSE 형식으로 전송
                data = json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n"
            
            # 완료 신호
            yield "data: [DONE]\n\n"
        
        except Exception as e:
            logger.error(f"스트리밍 중 오류: {e}", exc_info=True)
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/health")
async def chat_health():
    """
    채팅 서비스 상태 확인
    
    Returns:
        상태 정보
    """
    return {
        "status": "ok",
        "service": "chat",
        "agents": ["router", "search", "answer", "processing", "management"]
    }

