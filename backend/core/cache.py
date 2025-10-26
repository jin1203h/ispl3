"""
메모리 기반 캐시 (Redis 대체)
Windows 환경에서 Redis를 사용할 수 없을 때 사용
"""
import asyncio
import json
import time
import logging
from typing import Optional, Dict, Any
from collections import OrderedDict
from threading import Lock

logger = logging.getLogger(__name__)


class MemoryCache:
    """메모리 기반 캐시 (Redis 대체)"""
    
    def __init__(self, max_size: int = 10000):
        """
        Args:
            max_size: 최대 캐시 크기 (LRU 방식)
        """
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._max_size = max_size
        self._lock = Lock()
        logger.info(f"MemoryCache 초기화 (max_size={max_size})")
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """만료 여부 확인"""
        if 'expires_at' not in entry:
            return False
        return time.time() > entry['expires_at']
    
    def _evict_if_needed(self):
        """LRU 방식으로 오래된 항목 제거"""
        while len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
    
    async def get(self, key: str) -> Optional[str]:
        """캐시에서 값 가져오기"""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # 만료 확인
            if self._is_expired(entry):
                del self._cache[key]
                return None
            
            # LRU 업데이트 (최근 사용)
            self._cache.move_to_end(key)
            
            return entry['value']
    
    async def set(self, key: str, value: str, ttl: int = 3600):
        """캐시에 값 저장"""
        with self._lock:
            expires_at = time.time() + ttl
            self._cache[key] = {
                'value': value,
                'expires_at': expires_at
            }
            self._cache.move_to_end(key)
            self._evict_if_needed()
    
    async def delete(self, key: str):
        """캐시에서 삭제"""
        with self._lock:
            self._cache.pop(key, None)
    
    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache[key]
            if self._is_expired(entry):
                del self._cache[key]
                return False
            
            return True
    
    async def get_json(self, key: str) -> Optional[dict]:
        """JSON 형식으로 가져오기"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error(f"JSON 파싱 오류 ({key})")
                return None
        return None
    
    async def set_json(self, key: str, value: dict, ttl: int = 3600):
        """JSON 형식으로 저장"""
        try:
            json_str = json.dumps(value, ensure_ascii=False)
            await self.set(key, json_str, ttl)
        except Exception as e:
            logger.error(f"JSON 저장 오류 ({key}): {e}")
    
    async def clear_pattern(self, pattern: str):
        """패턴에 맞는 모든 키 삭제"""
        with self._lock:
            # 간단한 패턴 매칭 (와일드카드 지원)
            pattern_prefix = pattern.rstrip('*')
            keys_to_delete = [
                key for key in self._cache.keys()
                if key.startswith(pattern_prefix)
            ]
            for key in keys_to_delete:
                del self._cache[key]
            
            logger.info(f"패턴 삭제 완료: {pattern} ({len(keys_to_delete)}개)")
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계"""
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'utilization': f"{len(self._cache) / self._max_size * 100:.1f}%"
            }


class CacheFacade:
    """Redis 또는 MemoryCache를 동적으로 사용하는 Facade"""
    
    def __init__(self):
        self._backend = None
        self._type = None
    
    async def connect(self):
        """캐시 백엔드 연결"""
        from core.config import settings
        
        # Redis 사용 시도
        try:
            if settings.CACHE_ENABLED:
                import redis.asyncio as redis
                self._backend = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                    decode_responses=True,
                    socket_connect_timeout=2
                )
                # 연결 테스트
                await self._backend.ping()
                self._type = "redis"
                logger.info(f"✅ Redis 연결 성공: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            logger.warning(f"⚠️ Redis 연결 실패, MemoryCache로 대체: {e}")
            self._backend = MemoryCache()
            self._type = "memory"
    
    async def disconnect(self):
        """캐시 연결 종료"""
        if self._type == "redis" and self._backend:
            await self._backend.close()
        self._backend = None
        self._type = None
    
    async def get(self, key: str) -> Optional[str]:
        """캐시에서 값 가져오기"""
        if not self._backend:
            await self.connect()
        return await self._backend.get(key)
    
    async def set(self, key: str, value: str, ttl: int = 3600):
        """캐시에 값 저장"""
        if not self._backend:
            await self.connect()
        
        if self._type == "redis":
            await self._backend.setex(key, ttl, value)
        else:
            await self._backend.set(key, value, ttl)
    
    async def delete(self, key: str):
        """캐시에서 삭제"""
        if not self._backend:
            await self.connect()
        await self._backend.delete(key)
    
    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        if not self._backend:
            await self.connect()
        
        if self._type == "redis":
            return await self._backend.exists(key) > 0
        else:
            return await self._backend.exists(key)
    
    async def get_json(self, key: str) -> Optional[dict]:
        """JSON 형식으로 가져오기"""
        if not self._backend:
            await self.connect()
        
        if self._type == "redis":
            value = await self._backend.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return None
            return None
        else:
            return await self._backend.get_json(key)
    
    async def set_json(self, key: str, value: dict, ttl: int = 3600):
        """JSON 형식으로 저장"""
        if not self._backend:
            await self.connect()
        
        if self._type == "redis":
            json_str = json.dumps(value, ensure_ascii=False)
            await self._backend.setex(key, ttl, json_str)
        else:
            await self._backend.set_json(key, value, ttl)
    
    async def clear_pattern(self, pattern: str):
        """패턴에 맞는 모든 키 삭제"""
        if not self._backend:
            await self.connect()
        
        if self._type == "redis":
            cursor = 0
            while True:
                cursor, keys = await self._backend.scan(cursor, match=pattern, count=100)
                if keys:
                    await self._backend.delete(*keys)
                if cursor == 0:
                    break
        else:
            await self._backend.clear_pattern(pattern)
    
    def get_cache_type(self) -> Optional[str]:
        """현재 사용 중인 캐시 타입 반환"""
        return self._type
    
    def get_cache_info(self) -> Dict[str, Any]:
        """캐시 정보 반환"""
        info = {
            "type": self._type or "not_connected",
            "connected": self._backend is not None
        }
        
        if self._type == "memory" and self._backend:
            info.update(self._backend.get_stats())
        
        return info


# 싱글톤 인스턴스 (자동으로 Redis 또는 MemoryCache 선택)
# - Redis 사용 가능 시: Redis 사용 (고성능)
# - Redis 불가 시: 메모리 캐시 사용 (Windows 환경 등)
cache = CacheFacade()

# 하위 호환성을 위한 별칭
redis_cache = cache


async def get_cache():
    """FastAPI 의존성 주입용"""
    if cache._backend is None:
        await cache.connect()
    return cache
