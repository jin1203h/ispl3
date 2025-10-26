"""
ISPL Backend 메인 애플리케이션
보험약관 기반 Agentic AI 시스템
"""
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

from core.config import settings
from core.database import get_engine
from core.cache import cache  # Redis 또는 메모리 캐시 (자동 선택)
from api import health

# 로깅 설정 (애플리케이션 시작 시)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 특정 로거 레벨 조정 (SQLAlchemy는 WARNING으로)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시
    logger.info("🚀 ISPL 애플리케이션 시작")
    logger.info(f"📊 데이터베이스: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'Not configured'}")
    logger.info("📝 로깅 레벨: INFO")
    
    # 캐시 연결 (캐싱 활성화 시)
    if settings.CACHE_ENABLED:
        try:
            await cache.connect()
            cache_type = cache.get_cache_type()
            
            if cache_type == "redis":
                logger.info(f"✅ Redis 캐시 활성화: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            elif cache_type == "memory":
                logger.info("✅ 메모리 캐시 활성화 (Redis 미사용)")
            else:
                logger.warning("⚠️ 캐시 타입 확인 불가")
        except Exception as e:
            logger.warning(f"⚠️ 캐시 연결 실패: {e}")
    else:
        logger.info("❌ 캐시 비활성화")
    
    yield
    
    # 종료 시
    await get_engine().dispose()
    if settings.CACHE_ENABLED:
        await cache.disconnect()
    logger.info("👋 ISPL 애플리케이션 종료")


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="ISPL - Insurance Policy AI System",
    description="보험약관 기반 Agentic AI 시스템",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip 압축 미들웨어 (응답 크기 60-80% 감소)
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,  # 1KB 이상만 압축
    compresslevel=6      # 압축 레벨 (1-9, 기본 6)
)

# 라우터 등록
app.include_router(health.router, tags=["Health"])

# PDF 처리 라우터 추가
from api import pdf
app.include_router(pdf.router, prefix="/api/pdf", tags=["PDF Processing"])

# 검색 라우터 추가
from api import search
app.include_router(search.router, tags=["Search"])

# 채팅 라우터 추가
from api import chat
app.include_router(chat.router, tags=["Chat"])

# 문서 관리 라우터 추가
from api import documents
app.include_router(documents.router, tags=["Documents"])

# 대화 이력 라우터 추가
from api import chat_history
app.include_router(chat_history.router, tags=["Chat History"])


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "ISPL - Insurance Policy AI System",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
