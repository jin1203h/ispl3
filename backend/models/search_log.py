"""
SearchLog ORM 모델
검색 로그를 저장합니다.
"""
from sqlalchemy import Column, Integer, String, Text, Float, TIMESTAMP, ForeignKey, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from core.database import Base


class SearchLog(Base):
    """검색 로그 모델"""
    
    __tablename__ = "search_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)  # 외래키 제약 제거 (users 테이블 미구현)
    query = Column(Text, nullable=False)
    query_intent = Column(String(50))  # 의도 분류 결과
    search_type = Column(String(20))  # 'vector', 'keyword', 'hybrid'
    results_count = Column(Integer)
    top_similarity_score = Column(Float)
    selected_document_ids = Column(ARRAY(Integer))  # 사용자가 클릭한 문서
    response_time_ms = Column(Integer)
    user_feedback = Column(String(20))  # 'positive', 'negative', null
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    
    # Relationship (User 모델 구현 시 추가 예정)
    # user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    # user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return (
            f"<SearchLog(id={self.id}, query='{self.query[:50]}...', "
            f"search_type={self.search_type}, results_count={self.results_count})>"
        )

