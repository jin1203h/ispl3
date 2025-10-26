"""
청크 저장소 서비스
document_chunks 테이블에 청크를 저장하고 관리합니다.
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import logging

from models.document_chunk import DocumentChunk
from services.chunker import Chunk

logger = logging.getLogger(__name__)


class ChunkRepository:
    """청크 저장소"""
    
    def __init__(self, session: AsyncSession):
        """
        초기화
        
        Args:
            session: 비동기 DB 세션
        """
        self.session = session
    
    async def save_chunks(
        self,
        chunks: List[Chunk],
        document_id: int
    ) -> List[DocumentChunk]:
        """
        청크 리스트를 저장합니다 (배치 삽입).
        
        Args:
            chunks: Chunk 리스트
            document_id: 문서 ID
        
        Returns:
            저장된 DocumentChunk 리스트
        """
        if not chunks:
            logger.warning("저장할 청크가 없습니다.")
            return []
        
        logger.info(f"청크 저장 시작: {len(chunks)}개 (document_id={document_id})")
        
        # 기존 청크 삭제 (중복 방지)
        await self.delete_chunks_by_document(document_id)
        
        # DocumentChunk ORM 객체 생성
        db_chunks = []
        for chunk in chunks:
            # 임베딩 추출
            embedding = chunk.metadata.get('embedding') if chunk.metadata else None
            
            # 필드 길이 제한 (스키마 제약에 맞춤)
            section_title = chunk.section_title[:200] if chunk.section_title else None
            clause_number = chunk.clause_number[:50] if chunk.clause_number else None
            
            db_chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                chunk_type=chunk.chunk_type,
                page_number=chunk.page_number,  # Vision의 물리적 순서
                pdf_page_number=chunk.pdf_page_number,  # PDF 내부 인쇄 페이지 번호
                section_title=section_title,
                clause_number=clause_number,
                content=chunk.content,
                content_hash=chunk.content_hash,
                token_count=chunk.token_count,
                meta_data=chunk.metadata,  # ORM 속성은 meta_data
                embedding=embedding,
                confidence_score=chunk.metadata.get('confidence_score', 1.0) if chunk.metadata else 1.0
            )
            db_chunks.append(db_chunk)
        
        # 배치 삽입
        try:
            self.session.add_all(db_chunks)
            await self.session.flush()  # commit 전에 flush로 ID 생성
            
            # content_tsv 생성 (애플리케이션 레벨)
            from sqlalchemy import text
            chunk_ids = [chunk.id for chunk in db_chunks]
            if chunk_ids:
                update_tsv_query = text("""
                    UPDATE document_chunks
                    SET content_tsv = to_tsvector('simple', content)
                    WHERE id = ANY(:chunk_ids)
                """)
                await self.session.execute(update_tsv_query, {"chunk_ids": chunk_ids})
                logger.info(f"content_tsv 생성 완료: {len(chunk_ids)}개 청크")
            
            await self.session.commit()
            
            # ID 갱신을 위해 새로고침
            for db_chunk in db_chunks:
                await self.session.refresh(db_chunk)
            
            logger.info(f"청크 저장 완료: {len(db_chunks)}개")
            return db_chunks
        
        except Exception as e:
            await self.session.rollback()
            logger.error(f"청크 저장 실패: {e}")
            raise
    
    async def get_chunks_by_document(
        self,
        document_id: int,
        limit: Optional[int] = None
    ) -> List[DocumentChunk]:
        """
        문서 ID로 청크를 조회합니다.
        
        Args:
            document_id: 문서 ID
            limit: 최대 조회 개수
        
        Returns:
            DocumentChunk 리스트
        """
        query = select(DocumentChunk).where(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        chunks = result.scalars().all()
        
        logger.info(f"청크 조회: {len(chunks)}개 (document_id={document_id})")
        return list(chunks)
    
    async def get_chunk_by_id(self, chunk_id: int) -> Optional[DocumentChunk]:
        """
        ID로 청크를 조회합니다.
        
        Args:
            chunk_id: 청크 ID
        
        Returns:
            DocumentChunk 또는 None
        """
        query = select(DocumentChunk).where(DocumentChunk.id == chunk_id)
        result = await self.session.execute(query)
        chunk = result.scalar_one_or_none()
        return chunk
    
    async def delete_chunks_by_document(self, document_id: int) -> int:
        """
        문서 ID로 청크를 삭제합니다.
        
        Args:
            document_id: 문서 ID
        
        Returns:
            삭제된 청크 수
        """
        query = delete(DocumentChunk).where(
            DocumentChunk.document_id == document_id
        )
        result = await self.session.execute(query)
        await self.session.commit()
        
        deleted_count = result.rowcount
        if deleted_count > 0:
            logger.info(f"청크 삭제: {deleted_count}개 (document_id={document_id})")
        
        return deleted_count
    
    async def check_duplicate(self, content_hash: str) -> bool:
        """
        content_hash로 중복을 확인합니다.
        
        Args:
            content_hash: SHA-256 해시
        
        Returns:
            중복 여부
        """
        query = select(DocumentChunk).where(
            DocumentChunk.content_hash == content_hash
        ).limit(1)
        result = await self.session.execute(query)
        chunk = result.scalar_one_or_none()
        return chunk is not None
    
    async def get_chunks_by_type(
        self,
        document_id: int,
        chunk_type: str
    ) -> List[DocumentChunk]:
        """
        문서 ID와 타입으로 청크를 조회합니다.
        
        Args:
            document_id: 문서 ID
            chunk_type: 청크 타입 ('text', 'table', 'image')
        
        Returns:
            DocumentChunk 리스트
        """
        query = select(DocumentChunk).where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.chunk_type == chunk_type
        ).order_by(DocumentChunk.chunk_index)
        
        result = await self.session.execute(query)
        chunks = result.scalars().all()
        
        logger.info(
            f"청크 조회 (type={chunk_type}): {len(chunks)}개 "
            f"(document_id={document_id})"
        )
        return list(chunks)
    
    async def count_chunks(self, document_id: int) -> int:
        """
        문서의 청크 개수를 반환합니다.
        
        Args:
            document_id: 문서 ID
        
        Returns:
            청크 개수
        """
        from sqlalchemy import func
        
        query = select(func.count(DocumentChunk.id)).where(
            DocumentChunk.document_id == document_id
        )
        result = await self.session.execute(query)
        count = result.scalar_one()
        return count

