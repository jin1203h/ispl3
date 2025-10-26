"""
헬스 체크 API
"""
from fastapi import APIRouter, status
from sqlalchemy import text

from core.database import SessionDep

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: SessionDep):
    """
    헬스 체크 엔드포인트
    데이터베이스 연결 상태 확인
    """
    try:
        # 데이터베이스 연결 테스트
        result = await db.execute(text("SELECT 1"))
        result.fetchone()
        
        # pgvector extension 확인
        pgvector_check = await db.execute(
            text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        )
        has_pgvector = pgvector_check.scalar()
        
        return {
            "status": "healthy",
            "database": "connected",
            "pgvector": "enabled" if has_pgvector else "disabled"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

