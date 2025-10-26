"""
Document ORM 모델
보험약관 문서를 저장합니다.
"""
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from core.database import Base


class Document(Base):
    """문서 모델"""
    
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size = Column(Integer)  # BIGINT in DB
    document_type = Column(String(50), nullable=False)  # 'policy', 'clause', 'faq', 'guideline'
    insurance_type = Column(String(50))  # 'life', 'auto', 'health', 'property'
    company_name = Column(String(100))
    version = Column(String(20))
    effective_date = Column(Date)
    expiry_date = Column(Date)
    status = Column(String(20), default='active')  # 'active', 'inactive', 'archived'
    upload_timestamp = Column(TIMESTAMP, server_default=func.now())
    processed_timestamp = Column(TIMESTAMP)
    total_pages = Column(Integer)
    processing_status = Column(String(20), default='pending')  # 'pending', 'processing', 'completed', 'failed'
    created_by = Column(Integer)
    updated_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationship
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return (
            f"<Document(id={self.id}, filename='{self.filename}', "
            f"type={self.document_type}, status={self.processing_status})>"
        )

