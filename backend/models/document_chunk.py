"""
DocumentChunk ORM 모델
벡터화된 텍스트 청크를 저장합니다.
"""
from sqlalchemy import Column, Integer, String, Text, Float, TIMESTAMP, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from core.database import Base


class DocumentChunk(Base):
    """문서 청크 모델"""
    
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_type = Column(String(20), nullable=False)  # 'text', 'table', 'image'
    page_number = Column(Integer)  # Vision의 물리적 순서 (1, 2, 3...)
    pdf_page_number = Column(Integer)  # PDF 내부 인쇄 페이지 번호
    section_title = Column(String(200))
    clause_number = Column(String(50))
    content = Column(Text, nullable=False)
    content_hash = Column(String(64))  # SHA-256 해시
    token_count = Column(Integer)
    meta_data = Column("metadata", JSON)  # JSONB in PostgreSQL (컬럼명은 metadata로 유지)
    embedding = Column(Vector(1536))  # OpenAI text-embedding-3-large
    confidence_score = Column(Float, default=1.0)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationship
    document = relationship("Document", back_populates="chunks")
    
    def __repr__(self):
        return (
            f"<DocumentChunk(id={self.id}, document_id={self.document_id}, "
            f"chunk_index={self.chunk_index}, type={self.chunk_type})>"
        )

