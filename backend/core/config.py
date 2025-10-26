"""
애플리케이션 설정 관리
환경 변수(.env 파일)에서 설정을 로드합니다.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    """
    애플리케이션 설정
    
    환경 변수 우선순위:
    1. 시스템 환경 변수
    2. .env 파일
    3. 기본값 (개발 환경용)
    """
    
    # 데이터베이스 (필수: .env에서 설정 필요)
    DATABASE_URL: str
    
    # OpenAI (필수: .env에서 설정 필요)
    OPENAI_API_KEY: str
    
    # Redis 캐싱 (.env에서 설정 가능)
    # Windows 환경에서는 Redis 없이 메모리 캐시 자동 사용
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    CACHE_TTL: int = 3600  # 캐시 유효 시간 (초)
    CACHE_ENABLED: bool = True  # 캐싱 활성화 여부
    
    # 애플리케이션
    APP_ENV: str = "development"
    DEBUG: bool = True
    # JWT 토큰 서명, 세션 암호화 등에 사용되는 비밀 키
    # 운영 환경에서는 반드시 .env에서 강력한 키로 설정
    # 생성: python -c "import secrets; print(secrets.token_urlsafe(32))"
    SECRET_KEY: str = "dev-only-secret-key-DO-NOT-USE-IN-PRODUCTION"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # 파일 업로드
    MAX_FILE_SIZE: int = 50000000  # 50MB
    UPLOAD_DIR: str = "uploads"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )


# 싱글톤 인스턴스
settings = Settings()

