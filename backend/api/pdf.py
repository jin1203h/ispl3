"""
PDF 업로드 및 처리 API
Processing Agent 기반으로 리팩토링

처리 방식:
- pymupdf: PyMuPDF4LLM으로 빠른 텍스트 추출
- vision: GPT-4 Vision으로 이미지 기반 추출  
- both: 하이브리드 방식 - PyMuPDF 텍스트를 Vision API의 컨텍스트로 활용
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse
import logging

from agents.processing_agent import processing_agent
from agents.state import create_initial_state
from core.config import settings
from core.database import SessionDep

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload_pdf(
    session: SessionDep,  # DB 세션
    file: UploadFile = File(...),
    method: str = Form("pymupdf"),  # FormData로 받음: "pymupdf", "vision", or "both"
    document_type: str = Form("policy"),  # 문서 타입
    insurance_type: str = Form(None),  # 보험 타입 (선택)
    company_name: str = Form(None)  # 보험사명 (선택)
):
    """
    PDF 파일 업로드 및 처리 (Processing Agent 기반)
    
    Args:
        file: 업로드된 PDF 파일
        method: 처리 방법
            - "pymupdf": PyMuPDF4LLM으로 빠른 텍스트 추출 (기본값)
            - "vision": GPT-4 Vision으로 이미지 기반 추출
            - "both": 하이브리드 방식 
              * PyMuPDF로 텍스트 추출 (빠르고 정확)
              * Vision API에 텍스트 + 이미지를 함께 제공
              * Vision이 텍스트를 검증하고 표/이미지/레이아웃 정보를 보완
        document_type: 문서 타입 (policy, term 등)
        insurance_type: 보험 타입 (선택)
        company_name: 보험사명 (선택)
        
    Returns:
        처리 결과
    """
    # method 검증 및 로깅
    logger.info(f"📥 PDF 업로드 요청: filename={file.filename}, method={method}")
    if method not in ["pymupdf", "vision", "both"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 method: {method}. 'pymupdf', 'vision', 'both' 중 선택하세요."
        )
    # 파일 검증
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF 파일만 업로드 가능합니다."
        )
    
    if file.size and file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"파일 크기는 {settings.MAX_FILE_SIZE / 1024 / 1024}MB 이하여야 합니다."
        )
    
    try:
        # 파일 데이터 읽기
        file_data = await file.read()
        logger.info(f"파일 읽기 완료: {len(file_data)} bytes")
        
        # State 생성
        state = create_initial_state("")
        state["task_type"] = "upload"
        state["file_data"] = file_data
        state["filename"] = file.filename
        state["processing_method"] = method
        state["document_type"] = document_type
        state["insurance_type"] = insurance_type
        state["company_name"] = company_name
        
        # Processing Agent 호출
        logger.info("Processing Agent 호출 시작")
        result = await processing_agent.process(state)
        
        # 결과 처리
        if result.get("error"):
            # 오류 발생
            error_msg = result.get("error")
            logger.error(f"Processing Agent 오류: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
        
        # 성공
        processing_result = result.get("processing_result", {})
        logger.info(f"Processing Agent 완료: {processing_result}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "PDF 처리 완료",
                "document_id": processing_result.get("document_id"),
                "filename": processing_result.get("filename"),
                "total_pages": processing_result.get("total_pages"),
                "total_chunks": processing_result.get("total_chunks"),
                "processing_time_ms": processing_result.get("processing_time", 0)
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF 업로드 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/test", status_code=status.HTTP_200_OK)
async def test_pdf_endpoint():
    """
    PDF API 테스트 엔드포인트
    """
    return {
        "message": "PDF API 정상 작동",
        "max_file_size_mb": settings.MAX_FILE_SIZE / 1024 / 1024,
        "upload_dir": settings.UPLOAD_DIR
    }

