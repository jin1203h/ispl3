"""
문서 관리 서비스
약관 목록 조회, 삭제, 다운로드 기능을 제공합니다.
"""
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DocumentManagementService:
    """문서 관리 서비스"""
    
    def __init__(self):
        """초기화"""
        pass
    
    async def list_documents(
        self,
        session: AsyncSession,
        filename: Optional[str] = None,
        document_type: Optional[str] = None,
        company_name: Optional[str] = None,
        status: str = 'active',
        sort_by: str = 'created_at',
        sort_order: str = 'desc',
        offset: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        문서 목록 조회 (필터링, 정렬, 페이지네이션)
        
        Args:
            session: DB 세션
            filename: 파일명 필터 (부분 일치)
            document_type: 문서 유형 필터
            company_name: 회사명 필터 (부분 일치)
            status: 상태 필터
            sort_by: 정렬 기준 ('created_at' or 'filename')
            sort_order: 정렬 순서 ('asc' or 'desc')
            offset: 오프셋
            limit: 제한
            
        Returns:
            문서 목록 및 메타데이터
        """
        from sqlalchemy import select, func
        from models.document import Document
        from models.document_chunk import DocumentChunk
        
        # 기본 쿼리
        stmt = select(Document).where(Document.status != 'deleted')
        
        # 필터링
        if filename:
            stmt = stmt.where(Document.filename.ilike(f'%{filename}%'))
        if document_type:
            stmt = stmt.where(Document.document_type == document_type)
        if company_name:
            stmt = stmt.where(Document.company_name.ilike(f'%{company_name}%'))
        
        # 전체 개수 조회 (페이지네이션 적용 전)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = (await session.execute(count_stmt)).scalar() or 0
        
        # 정렬
        order_col = Document.upload_timestamp if sort_by == 'created_at' else Document.filename
        stmt = stmt.order_by(order_col.desc() if sort_order == 'desc' else order_col.asc())
        
        # 페이지네이션
        stmt = stmt.offset(offset).limit(limit)
        
        result = await session.execute(stmt)
        documents = result.scalars().all()
        
        # 청크 수 조회 및 응답 구성
        documents_list = []
        for doc in documents:
            chunk_count_stmt = select(func.count(DocumentChunk.id)).where(
                DocumentChunk.document_id == doc.id
            )
            chunk_count = (await session.execute(chunk_count_stmt)).scalar() or 0
            documents_list.append({
                "id": doc.id,
                "filename": doc.filename,
                "document_type": doc.document_type,
                "company_name": doc.company_name,
                "status": doc.status,
                "created_at": doc.upload_timestamp.isoformat() if doc.upload_timestamp else None,
                "total_pages": doc.total_pages,
                "total_chunks": chunk_count
            })
        
        logger.info(f"문서 목록 조회 완료: {len(documents_list)}개 문서 (전체: {total_count}개)")
        
        return {
            "documents": documents_list,
            "total": total_count,
            "offset": offset,
            "limit": limit
        }
    
    async def get_document(
        self,
        session: AsyncSession,
        document_id: int
    ) -> Dict[str, Any]:
        """
        문서 상세 조회
        
        Args:
            session: DB 세션
            document_id: 문서 ID
            
        Returns:
            문서 상세 정보
        """
        from sqlalchemy import select, func
        from models.document import Document
        from models.document_chunk import DocumentChunk
        
        # 문서 조회
        stmt = select(Document).where(Document.id == document_id)
        result = await session.execute(stmt)
        document = result.scalar_one_or_none()
        
        if not document:
            return {
                "success": False,
                "error": f"문서를 찾을 수 없습니다: ID={document_id}"
            }
        
        # 청크 수 조회
        chunk_count_stmt = select(func.count(DocumentChunk.id)).where(
            DocumentChunk.document_id == document_id
        )
        chunk_count = (await session.execute(chunk_count_stmt)).scalar() or 0
        
        logger.info(f"문서 조회 완료: ID={document_id}")
        
        return {
            "success": True,
            "document": {
                "id": document.id,
                "filename": document.filename,
                "file_path": document.file_path,
                "document_type": document.document_type,
                "company_name": document.company_name,
                "status": document.status,
                "created_at": document.upload_timestamp.isoformat() if document.upload_timestamp else None,
                "updated_at": document.updated_at.isoformat() if document.updated_at else None,
                "file_size": document.file_size,
                "total_pages": document.total_pages,
                "total_chunks": chunk_count
            }
        }
    
    async def delete_document(
        self,
        session: AsyncSession,
        document_id: int
    ) -> Dict[str, Any]:
        """
        문서 삭제 (DB + 로컬 파일)
        
        Args:
            session: DB 세션
            document_id: 문서 ID
            
        Returns:
            삭제 결과
        """
        from pathlib import Path
        from fastapi import HTTPException, status
        from models.document import Document
        
        # 1. 문서 조회
        document = await session.get(Document, document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"문서를 찾을 수 없습니다: ID={document_id}"
            )
        
        # 2. 파일 경로 확보
        pdf_path = Path(document.file_path)
        filename = document.filename
        
        # MD 파일 찾기 (여러 패턴 시도)
        stem = pdf_path.stem
        parent = pdf_path.parent
        md_paths = [
            pdf_path.with_suffix('.md'),           # 기본: filename.md
            parent / f"{stem}_vision.md",          # vision 방식
            parent / f"{stem}_both.md",            # both 방식
        ]
        
        # 3. DB 삭제 (chunks는 CASCADE로 자동 삭제)
        await session.delete(document)
        await session.commit()
        logger.info(f"DB 레코드 삭제 완료: ID={document_id}")
        
        # 4. 파일 삭제 (커밋 후)
        deleted_files = []
        # PDF 삭제
        if pdf_path.exists():
            try:
                pdf_path.unlink()
                deleted_files.append(str(pdf_path))
                logger.info(f"파일 삭제 완료: {pdf_path}")
            except Exception as e:
                logger.error(f"파일 삭제 실패: {pdf_path}, {e}")
        
        # MD 삭제 (존재하는 것만)
        for md_path in md_paths:
            if md_path.exists():
                try:
                    md_path.unlink()
                    deleted_files.append(str(md_path))
                    logger.info(f"파일 삭제 완료: {md_path}")
                except Exception as e:
                    logger.error(f"파일 삭제 실패: {md_path}, {e}")
        
        return {
            "success": True,
            "message": "문서가 삭제되었습니다",
            "document_id": document_id,
            "filename": filename,
            "deleted_files": deleted_files
        }
    
    async def get_document_file_path(
        self,
        session: AsyncSession,
        document_id: int,
        file_type: str = 'pdf'
    ) -> Path:
        """
        문서 파일 경로 조회 (다운로드용)
        
        Args:
            session: DB 세션
            document_id: 문서 ID
            file_type: 파일 유형 ('pdf' or 'markdown')
            
        Returns:
            파일 경로
        """
        from pathlib import Path
        from fastapi import HTTPException, status
        from models.document import Document
        
        # 문서 조회
        document = await session.get(Document, document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"문서를 찾을 수 없습니다: ID={document_id}"
            )
        
        # 파일 경로 결정
        pdf_path = Path(document.file_path)
        if file_type == 'pdf':
            file_path = pdf_path
        elif file_type == 'markdown':
            file_path = pdf_path.with_suffix('.md')
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="file_type은 'pdf' 또는 'markdown'이어야 합니다"
            )
        
        # 파일 존재 확인
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{file_type} 파일이 존재하지 않습니다"
            )
        
        logger.info(f"파일 다운로드 요청: ID={document_id}, type={file_type}, path={file_path}")
        return file_path
    
    async def get_document_content(
        self,
        session: AsyncSession,
        document_id: int,
        file_type: str = 'pdf'
    ) -> Dict[str, Any]:
        """
        문서 내용 조회 (뷰어용)
        
        Args:
            session: DB 세션
            document_id: 문서 ID
            file_type: 파일 유형 ('pdf' or 'markdown')
            
        Returns:
            문서 내용 또는 URL
        """
        from pathlib import Path
        from fastapi import HTTPException, status
        from models.document import Document
        
        # 문서 조회
        document = await session.get(Document, document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"문서를 찾을 수 없습니다: ID={document_id}"
            )
        
        pdf_path = Path(document.file_path)
        
        if file_type == 'markdown':
            # Markdown 파일 찾기: 여러 패턴 시도
            stem = pdf_path.stem  # 확장자 제외한 파일명
            parent = pdf_path.parent
            
            # 1. 기본: filename.md
            md_path = pdf_path.with_suffix('.md')
            
            # 2. filename_ID_vision.md 패턴
            if not md_path.exists():
                md_path = parent / f"{stem}_vision.md"
            
            # 3. filename_ID_both.md 패턴
            if not md_path.exists():
                md_path = parent / f"{stem}_both.md"
            
            if not md_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Markdown 파일이 존재하지 않습니다"
                )
            
            try:
                content = md_path.read_text(encoding='utf-8')
                logger.info(f"Markdown 조회: ID={document_id}, size={len(content)} bytes")
                return {
                    'type': 'markdown',
                    'content': content,
                    'filename': md_path.name,
                    'document_id': document_id
                }
            except UnicodeDecodeError as e:
                logger.error(f'Markdown 인코딩 오류: ID={document_id}, {e}')
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='Markdown 파일 읽기 실패 (인코딩 오류)'
                )
        else:  # pdf
            if not pdf_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="PDF 파일이 존재하지 않습니다"
                )
            
            logger.info(f"PDF 조회: ID={document_id}, path={pdf_path}")
            return {
                'type': 'pdf',
                'url': f'/api/documents/{document_id}/download?file_type=pdf&inline=true',
                'filename': pdf_path.name,
                'document_id': document_id,
                'file_size': document.file_size,
                'total_pages': document.total_pages
            }

