"""
임베딩 캐싱 서비스
- Redis 또는 메모리 캐시를 사용하여 임베딩 결과를 캐싱
- 동일한 텍스트에 대한 OpenAI API 호출 최소화
"""
import hashlib
import logging
from typing import List, Optional
import json

from core.cache import cache
from core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingCacheService:
    """임베딩 캐시 서비스"""
    
    def __init__(self):
        self.cache_prefix = "embedding"
        self.ttl = settings.CACHE_TTL
    
    def _get_cache_key(self, text: str, model: str = "text-embedding-3-large") -> str:
        """캐시 키 생성"""
        # 텍스트 해시 생성 (동일 텍스트 식별)
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return f"{self.cache_prefix}:{model}:{text_hash}"
    
    async def get_embedding(self, text: str, model: str = "text-embedding-3-large") -> Optional[List[float]]:
        """캐시에서 임베딩 가져오기"""
        if not settings.CACHE_ENABLED:
            return None
        
        try:
            key = self._get_cache_key(text, model)
            cached_value = await cache.get(key)
            
            if cached_value:
                embedding = json.loads(cached_value)
                logger.debug(f"임베딩 캐시 HIT: {text[:50]}...")
                return embedding
            
            logger.debug(f"임베딩 캐시 MISS: {text[:50]}...")
            return None
        
        except Exception as e:
            logger.error(f"임베딩 캐시 조회 오류: {e}")
            return None
    
    async def set_embedding(self, text: str, embedding: List[float], model: str = "text-embedding-3-large"):
        """캐시에 임베딩 저장"""
        if not settings.CACHE_ENABLED:
            return
        
        try:
            key = self._get_cache_key(text, model)
            value = json.dumps(embedding)
            await cache.set(key, value, self.ttl)
            logger.debug(f"임베딩 캐시 저장: {text[:50]}...")
        
        except Exception as e:
            logger.error(f"임베딩 캐시 저장 오류: {e}")
    
    async def get_batch_embeddings(
        self,
        texts: List[str],
        model: str = "text-embedding-3-large"
    ) -> List[Optional[List[float]]]:
        """배치로 임베딩 가져오기"""
        results = []
        for text in texts:
            embedding = await self.get_embedding(text, model)
            results.append(embedding)
        return results
    
    async def set_batch_embeddings(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        model: str = "text-embedding-3-large"
    ):
        """배치로 임베딩 저장"""
        for text, embedding in zip(texts, embeddings):
            await self.set_embedding(text, embedding, model)
    
    async def clear_cache(self):
        """임베딩 캐시 전체 삭제"""
        try:
            await cache.clear_pattern(f"{self.cache_prefix}:*")
            logger.info("임베딩 캐시 전체 삭제 완료")
        except Exception as e:
            logger.error(f"임베딩 캐시 삭제 오류: {e}")


# 싱글톤 인스턴스
embedding_cache_service = EmbeddingCacheService()

