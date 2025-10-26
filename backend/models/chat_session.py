"""
대화 세션 모델
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from core.database import Base


class ChatSession(Base):
    """대화 세션"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)  # 외래키 제약 제거
    title = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    message_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ChatSession(id={self.id}, thread_id='{self.thread_id}', title='{self.title}')>"



