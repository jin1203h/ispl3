"""
Processing Agent
PDF 업로드 및 전처리를 담당하는 Agent
"""
import logging
from pathlib import Path
from datetime import datetime
import shutil
from typing import Optional

from agents.state import ISPLState
from services.service_container import get_pdf_processor
from core.config import settings
from core.database import AsyncSessionLocal
from models.document import Document

logger = logging.getLogger(__name__)


class ProcessingAgent:
    """PDF 업로드 및 전처리를 담당하는 Agent"""
    
    def __init__(self):
        """Processing Agent 초기화 (서비스 컨테이너에서 싱글톤 인스턴스 사용)"""
        # 서비스 컨테이너에서 싱글톤 인스턴스 가져오기
        self.pdf_processor = get_pdf_processor()
        logger.info("ProcessingAgent 초기화 완료 (싱글톤 서비스 사용)")
    
    async def _save_file(
        self,
        file_data: bytes,
        filename: str,
        document_id: Optional[int] = None
    ) -> Path:
        """
        파일을 저장합니다.
        
        Args:
            file_data: 파일 바이너리 데이터
            filename: 원본 파일명
            document_id: 문서 ID (선택)
        
        Returns:
            저장된 파일 경로
        """
        upload_dir = Path(settings.UPLOAD_DIR) / "documents"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일명 생성
        timestamp = int(datetime.now().timestamp())
        original_name = Path(filename).stem
        
        if document_id:
            pdf_filename = f"{original_name}_{document_id}.pdf"
        else:
            pdf_filename = f"{original_name}_{timestamp}.pdf"
        
        pdf_path = upload_dir / pdf_filename
        
        # 파일 저장
        with pdf_path.open("wb") as f:
            f.write(file_data)
        
        logger.info(f"파일 저장 완료: {pdf_path}")
        
        return pdf_path
    
    async def _create_document(
        self,
        pdf_path: Path,
        original_filename: str,
        document_type: str = "policy",
        insurance_type: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> int:
        """
        Document 레코드를 생성합니다.
        
        Args:
            pdf_path: PDF 파일 경로
            original_filename: 원본 파일명
            document_type: 문서 타입
            insurance_type: 보험 타입
            company_name: 보험사명
        
        Returns:
            생성된 문서 ID
        """
        session = AsyncSessionLocal()
        
        try:
            file_size = pdf_path.stat().st_size
            
            document = Document(
                filename=pdf_path.name,
                original_filename=original_filename,
                file_path=str(pdf_path),
                file_size=file_size,
                document_type=document_type,
                insurance_type=insurance_type,
                company_name=company_name,
                processing_status="processing"
            )
            
            session.add(document)
            await session.flush()  # ID 생성
            
            document_id = document.id
            await session.commit()
            
            logger.info(f"Document 레코드 생성: ID={document_id}")
            
            return document_id
        
        finally:
            await session.close()
    
    async def _update_document_status(
        self,
        document_id: int,
        status: str,
        total_pages: Optional[int] = None
    ):
        """
        Document 상태를 업데이트합니다.
        
        Args:
            document_id: 문서 ID
            status: 처리 상태
            total_pages: 총 페이지 수
        """
        session = AsyncSessionLocal()
        
        try:
            from sqlalchemy import select
            
            stmt = select(Document).where(Document.id == document_id)
            result = await session.execute(stmt)
            document = result.scalar_one_or_none()
            
            if document:
                document.processing_status = status
                if status == "completed":
                    document.processed_timestamp = datetime.now()
                if total_pages:
                    document.total_pages = total_pages
                
                await session.commit()
                
                logger.info(f"Document 상태 업데이트: ID={document_id}, status={status}")
        
        finally:
            await session.close()
    
    async def _update_document_file_info(
        self,
        document_id: int,
        file_path: Path
    ):
        """
        Document의 파일 정보를 업데이트합니다.
        
        Args:
            document_id: 문서 ID
            file_path: 새로운 파일 경로
        """
        session = AsyncSessionLocal()
        
        try:
            from sqlalchemy import select
            
            stmt = select(Document).where(Document.id == document_id)
            result = await session.execute(stmt)
            document = result.scalar_one_or_none()
            
            if document:
                document.filename = file_path.name
                document.file_path = str(file_path)
                
                await session.commit()
                
                logger.info(f"Document 파일 정보 업데이트: ID={document_id}, filename={file_path.name}")
        
        finally:
            await session.close()
    
    async def process(self, state: ISPLState) -> dict:
        """
        PDF 파일을 처리합니다.
        
        처리 단계:
        1. 파일 저장
        2. Document 레코드 생성
        3. PDF 전처리 (PyMuPDF + Vision)
        4. 청킹 및 임베딩
        5. 벡터 DB 저장
        
        Args:
            state: 현재 상태
        
        Returns:
            업데이트할 상태 딕셔너리
        """
        # state에서 파일 정보 추출
        file_data = state.get("file_data")
        filename = state.get("filename", "upload.pdf")
        processing_method = state.get("processing_method", "pymupdf")
        document_type = state.get("document_type", "policy")
        insurance_type = state.get("insurance_type")
        company_name = state.get("company_name")
        
        if not file_data:
            logger.error("파일 데이터가 없습니다")
            return {
                "error": "파일 데이터가 없습니다",
                "processing_result": None,
                "task_results": {
                    "processing": {
                        "success": False,
                        "error": "파일 데이터가 없습니다"
                    }
                }
            }
        
        try:
            logger.info(
                f"PDF 처리 시작: filename={filename}, "
                f"method={processing_method}"
            )
            
            # 1. 파일 임시 저장 (document_id 없이)
            pdf_path = await self._save_file(file_data, filename)
            
            # 2. Document 레코드 생성
            document_id = await self._create_document(
                pdf_path,
                filename,
                document_type,
                insurance_type,
                company_name
            )
            
            # 3. 파일명 업데이트 (document_id 포함)
            final_pdf_path = await self._save_file(
                file_data,
                filename,
                document_id
            )
            
            # 기존 파일 삭제
            if pdf_path != final_pdf_path and pdf_path.exists():
                pdf_path.unlink()
                logger.info(f"임시 파일 삭제: {pdf_path}")
            
            pdf_path = final_pdf_path
            
            # Document 레코드의 파일 정보 업데이트
            await self._update_document_file_info(document_id, pdf_path)
            
            # 4. PDF 처리 (청킹 및 임베딩 포함)
            session = AsyncSessionLocal()
            
            try:
                result = await self.pdf_processor.process_pdf(
                    str(pdf_path),
                    document_id,
                    save_markdown=True,
                    method=processing_method,
                    enable_chunking=True,  # 항상 활성화
                    db_session=session
                )
                
                if result['status'] == 'success':
                    # 5. Document 상태 업데이트
                    total_pages = result['data']['metadata'].get('total_pages')
                    await self._update_document_status(
                        document_id,
                        "completed",
                        total_pages
                    )
                    
                    total_chunks = result['data'].get('chunks', {}).get('total_chunks', 0)
                    
                    logger.info(
                        f"PDF 처리 완료: document_id={document_id}, "
                        f"pages={total_pages}, chunks={total_chunks}"
                    )
                    
                    return {
                        "processing_result": {
                            "document_id": document_id,
                            "filename": filename,
                            "total_pages": total_pages,
                            "total_chunks": total_chunks,
                            "processing_time": result.get('processing_time_ms', 0)
                        },
                        "task_results": {
                            "processing": {
                                "success": True,
                                "document_id": document_id,
                                "total_chunks": total_chunks
                            }
                        },
                        "final_answer": (
                            f"✅ 약관 등록 완료!\n\n"
                            f"**문서 정보**\n"
                            f"- 파일명: {filename}\n"
                            f"- 페이지: {total_pages}페이지\n"
                            f"- 청크: {total_chunks}개\n\n"
                            f"이제 이 약관에 대해 질문하실 수 있습니다."
                        ),
                        "error": None
                    }
                else:
                    # 처리 실패
                    await self._update_document_status(document_id, "failed")
                    
                    error_msg = result.get('error', '알 수 없는 오류')
                    logger.error(f"PDF 처리 실패: {error_msg}")
                    
                    return {
                        "error": f"PDF 처리 실패: {error_msg}",
                        "processing_result": None,
                        "task_results": {
                            "processing": {
                                "success": False,
                                "error": error_msg
                            }
                        },
                        "final_answer": f"죄송합니다. 파일 처리 중 오류가 발생했습니다: {error_msg}"
                    }
            
            finally:
                await session.close()
        
        except Exception as e:
            logger.error(f"Processing Agent 오류: {e}", exc_info=True)
            
            return {
                "error": str(e),
                "processing_result": None,
                "task_results": {
                    "processing": {
                        "success": False,
                        "error": str(e)
                    }
                },
                "final_answer": f"죄송합니다. 파일 처리 중 오류가 발생했습니다: {str(e)}"
            }


# 전역 Processing Agent 인스턴스
processing_agent = ProcessingAgent()


async def processing_node(state: ISPLState) -> dict:
    """
    Processing Agent 노드 함수
    
    Args:
        state: 현재 상태
    
    Returns:
        업데이트할 상태 딕셔너리
    """
    return await processing_agent.process(state)

