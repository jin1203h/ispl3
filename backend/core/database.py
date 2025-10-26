"""
데이터베이스 연결 및 세션 관리
SQLAlchemy 비동기 엔진 설정
"""
from typing import AsyncGenerator, Annotated
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from sqlalchemy.pool import NullPool
from fastapi import Depends

from core.config import settings


# 전역 엔진 변수 (지연 생성)
_engine = None


def get_engine():
    """
    엔진을 반환합니다 (지연 생성).
    
    이벤트 루프 문제를 방지하기 위해 첫 호출 시 엔진을 생성합니다.
    테스트 환경에서는 NullPool을 사용하여 연결 재사용 문제를 방지합니다.
    
    Returns:
        AsyncEngine
    """
    global _engine
    
    if _engine is None:
        # 테스트 환경 감지
        is_testing = os.getenv("TESTING", "false").lower() == "true" or "pytest" in sys.modules
        
        # SQLAlchemy 엔진 생성 (비동기)
        if is_testing:
            _engine = create_async_engine(
                settings.DATABASE_URL,
                echo=settings.DEBUG,
                future=True,
                poolclass=NullPool,  # 테스트: 연결 풀링 비활성화
            )
        else:
            _engine = create_async_engine(
                settings.DATABASE_URL,
                echo=settings.DEBUG,
                future=True,
                pool_pre_ping=True,        # 연결 유효성 자동 확인
                pool_size=20,              # 기본 연결 수 (10 → 20)
                max_overflow=30,           # 추가 연결 수 (20 → 30)
                pool_recycle=3600,         # 1시간마다 연결 재생성
                pool_timeout=30,           # 연결 대기 타임아웃
                connect_args={
                    "server_settings": {
                        "application_name": "ispl_backend",  # 디버깅용
                        "jit": "off",                        # JIT 비활성화 (성능 향상)
                    }
                }
            )
        
        # pgvector 타입 등록 (asyncpg 연결 시)
        @event.listens_for(_engine.sync_engine, "connect")
        def register_vector_types(dbapi_connection, connection_record):
            """asyncpg 연결 시 pgvector 타입을 등록합니다."""
            from pgvector.asyncpg import register_vector
            
            # asyncpg 연결은 비동기이므로 run_async로 실행
            dbapi_connection.run_async(register_vector)
    
    return _engine


# 비동기 세션 팩토리 (지연 생성)
_AsyncSessionLocal = None


def get_session_factory():
    """
    세션 팩토리를 반환합니다 (지연 생성).
    
    Returns:
        async_sessionmaker
    """
    global _AsyncSessionLocal
    
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    
    return _AsyncSessionLocal


# 하위 호환성을 위한 함수
def AsyncSessionLocal():
    """세션을 생성합니다."""
    factory = get_session_factory()
    return factory()


class Base(DeclarativeBase):
    """SQLAlchemy Base 클래스"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    데이터베이스 세션 의존성
    
    Yields:
        AsyncSession: 비동기 데이터베이스 세션
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# 의존성 주입을 위한 타입 어노테이션
SessionDep = Annotated[AsyncSession, Depends(get_db)]

