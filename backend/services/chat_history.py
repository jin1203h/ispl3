"""
대화 이력 관리 서비스
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from models.chat_session import ChatSession
from models.chat_message import ChatMessage

logger = logging.getLogger(__name__)


class ChatHistoryService:
    """대화 이력 관리 서비스"""
    
    async def create_or_get_session(
        self,
        session: AsyncSession,
        thread_id: str,
        user_id: Optional[int] = None,
        title: Optional[str] = None
    ) -> ChatSession:
        """
        세션을 생성하거나 기존 세션을 가져옵니다.
        
        Args:
            session: DB 세션
            thread_id: 스레드 ID
            user_id: 사용자 ID
            title: 대화 제목
        
        Returns:
            ChatSession
        """
        # 기존 세션 조회
        stmt = select(ChatSession).where(ChatSession.thread_id == thread_id)
        result = await session.execute(stmt)
        chat_session = result.scalar_one_or_none()
        
        if chat_session:
            logger.info(f"기존 세션 찾음: thread_id={thread_id}")
            return chat_session
        
        # 새 세션 생성
        chat_session = ChatSession(
            thread_id=thread_id,
            user_id=user_id,
            title=title or f"대화 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        session.add(chat_session)
        await session.commit()
        await session.refresh(chat_session)
        
        logger.info(f"새 세션 생성: thread_id={thread_id}, session_id={chat_session.id}")
        return chat_session
    
    async def save_message(
        self,
        session: AsyncSession,
        thread_id: str,
        role: str,
        content: str,
        message_metadata: Optional[Dict] = None
    ) -> ChatMessage:
        """
        메시지를 저장합니다.
        
        Args:
            session: DB 세션
            thread_id: 스레드 ID
            role: 역할 ('user', 'assistant', 'system')
            content: 메시지 내용
            message_metadata: 메타데이터
        
        Returns:
            ChatMessage
        """
        # 세션 가져오기
        chat_session = await self.create_or_get_session(session, thread_id)
        
        # 메시지 생성
        message = ChatMessage(
            session_id=chat_session.id,
            role=role,
            content=content,
            message_metadata=message_metadata
        )
        session.add(message)
        
        # message_count 증가 및 updated_at 업데이트
        chat_session.message_count += 1
        
        await session.commit()
        await session.refresh(message)
        
        logger.info(f"메시지 저장: session_id={chat_session.id}, role={role}")
        return message
    
    async def get_session_messages(
        self,
        session: AsyncSession,
        thread_id: str,
        limit: Optional[int] = None
    ) -> List[ChatMessage]:
        """
        세션의 메시지 목록을 조회합니다.
        
        Args:
            session: DB 세션
            thread_id: 스레드 ID
            limit: 제한 (최근 N개)
        
        Returns:
            메시지 목록
        """
        # 세션 조회
        stmt = select(ChatSession).where(ChatSession.thread_id == thread_id)
        result = await session.execute(stmt)
        chat_session = result.scalar_one_or_none()
        
        if not chat_session:
            return []
        
        # 메시지 조회
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == chat_session.id)
            .order_by(ChatMessage.created_at)
        )
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = await session.execute(stmt)
        messages = result.scalars().all()
        
        logger.info(f"메시지 조회: thread_id={thread_id}, count={len(messages)}")
        return list(messages)
    
    async def list_sessions(
        self,
        session: AsyncSession,
        user_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        세션 목록을 조회합니다.
        
        Args:
            session: DB 세션
            user_id: 사용자 ID
            limit: 제한
            offset: 오프셋
        
        Returns:
            세션 목록 및 메타데이터
        """
        # 기본 쿼리
        stmt = select(ChatSession).where(ChatSession.is_active == True)
        
        if user_id:
            stmt = stmt.where(ChatSession.user_id == user_id)
        
        # 전체 개수
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await session.execute(count_stmt)).scalar() or 0
        
        # 정렬 및 페이지네이션
        stmt = stmt.order_by(desc(ChatSession.updated_at)).offset(offset).limit(limit)
        
        result = await session.execute(stmt)
        sessions = result.scalars().all()
        
        # 응답 구성
        sessions_list = []
        for s in sessions:
            sessions_list.append({
                "id": s.id,
                "thread_id": s.thread_id,
                "title": s.title,
                "message_count": s.message_count,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None
            })
        
        logger.info(f"세션 목록 조회: count={len(sessions_list)}, total={total}")
        
        return {
            "sessions": sessions_list,
            "total": total,
            "offset": offset,
            "limit": limit
        }
    
    async def update_session_title(
        self,
        session: AsyncSession,
        thread_id: str,
        title: str
    ) -> bool:
        """
        세션 제목을 업데이트합니다.
        
        Args:
            session: DB 세션
            thread_id: 스레드 ID
            title: 새 제목
        
        Returns:
            성공 여부
        """
        stmt = select(ChatSession).where(ChatSession.thread_id == thread_id)
        result = await session.execute(stmt)
        chat_session = result.scalar_one_or_none()
        
        if not chat_session:
            return False
        
        chat_session.title = title
        await session.commit()
        
        logger.info(f"세션 제목 업데이트: thread_id={thread_id}, title={title}")
        return True
    
    async def delete_session(
        self,
        session: AsyncSession,
        thread_id: str
    ) -> bool:
        """
        세션을 삭제합니다 (soft delete).
        
        Args:
            session: DB 세션
            thread_id: 스레드 ID
        
        Returns:
            성공 여부
        """
        stmt = select(ChatSession).where(ChatSession.thread_id == thread_id)
        result = await session.execute(stmt)
        chat_session = result.scalar_one_or_none()
        
        if not chat_session:
            return False
        
        chat_session.is_active = False
        await session.commit()
        
        logger.info(f"세션 삭제: thread_id={thread_id}")
        return True



