"""
임베딩 생성 서비스
OpenAI text-embedding-3-large를 사용하여 텍스트 임베딩을 생성합니다.
"""
import asyncio
from typing import List, Dict, Any
import logging
from openai import AsyncOpenAI
import tenacity

from core.config import settings
from services.chunker import Chunk
from services.embedding_cache import embedding_cache_service

logger = logging.getLogger(__name__)


class EmbeddingService:
    """임베딩 생성 서비스"""
    
    MODEL_NAME = "text-embedding-3-large"
    EMBEDDING_DIM = 1536
    BATCH_SIZE = 100  # OpenAI API 배치 크기
    
    def __init__(self):
        """초기화"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.semaphore = asyncio.Semaphore(5)  # 동시 요청 제한
        logger.info(
            f"EmbeddingService 초기화: model={self.MODEL_NAME}, "
            f"dim={self.EMBEDDING_DIM}"
        )
    
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(min=1, max=10),
        retry=tenacity.retry_if_exception_type(Exception),
        before_sleep=tenacity.before_sleep_log(logger, logging.WARNING)
    )
    async def _create_embedding_with_retry(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """
        재시도 로직이 포함된 임베딩 생성
        
        Args:
            texts: 텍스트 리스트
        
        Returns:
            임베딩 벡터 리스트
        """
        async with self.semaphore:
            response = await self.client.embeddings.create(
                model=self.MODEL_NAME,
                input=texts,
                dimensions=self.EMBEDDING_DIM  # 1536 차원으로 명시
            )
            embeddings = [data.embedding for data in response.data]
            return embeddings
    
    async def create_embedding(self, text: str) -> List[float]:
        """
        단일 텍스트의 임베딩을 생성합니다.
        캐시를 먼저 확인하고, 없으면 OpenAI API 호출 후 캐싱합니다.
        
        Args:
            text: 입력 텍스트
        
        Returns:
            임베딩 벡터 (1536차원)
        """
        if not text or len(text.strip()) == 0:
            logger.warning("빈 텍스트가 입력되었습니다. 제로 벡터 반환.")
            return [0.0] * self.EMBEDDING_DIM
        
        try:
            # 1. 캐시 확인
            cached_embedding = await embedding_cache_service.get_embedding(text, self.MODEL_NAME)
            if cached_embedding:
                return cached_embedding
            
            # 2. 캐시 미스 - OpenAI API 호출
            embeddings = await self._create_embedding_with_retry([text])
            embedding = embeddings[0]
            
            # 3. 캐시에 저장
            await embedding_cache_service.set_embedding(text, embedding, self.MODEL_NAME)
            
            return embedding
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}")
            raise
    
    async def create_embeddings_batch(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """
        여러 텍스트의 임베딩을 배치로 생성합니다.
        캐시를 활용하여 중복 호출을 최소화합니다.
        
        Args:
            texts: 텍스트 리스트
        
        Returns:
            임베딩 벡터 리스트
        """
        if not texts:
            return []
        
        logger.info(f"배치 임베딩 생성 시작: {len(texts)}개")
        
        # 1. 캐시에서 임베딩 조회
        cached_embeddings = await embedding_cache_service.get_batch_embeddings(texts, self.MODEL_NAME)
        
        # 2. 캐시 미스 텍스트 찾기
        texts_to_create = []
        result_embeddings = []
        cache_hits = 0
        
        for i, (text, cached) in enumerate(zip(texts, cached_embeddings)):
            if cached:
                result_embeddings.append((i, cached))
                cache_hits += 1
            else:
                texts_to_create.append((i, text))
        
        logger.info(f"캐시 HIT: {cache_hits}개, MISS: {len(texts_to_create)}개")
        
        # 3. 캐시 미스 텍스트의 임베딩 생성
        if texts_to_create:
            # 배치로 분할
            texts_only = [text for _, text in texts_to_create]
            batches = [
                texts_only[i:i + self.BATCH_SIZE]
                for i in range(0, len(texts_only), self.BATCH_SIZE)
            ]
            
            # 각 배치를 병렬로 처리
            new_embeddings = []
            for i, batch in enumerate(batches):
                logger.info(f"배치 {i+1}/{len(batches)} 처리 중 ({len(batch)}개)")
                try:
                    embeddings = await self._create_embedding_with_retry(batch)
                    new_embeddings.extend(embeddings)
                except Exception as e:
                    logger.error(f"배치 {i+1} 임베딩 생성 실패: {e}")
                    # 실패한 배치는 제로 벡터로 대체
                    new_embeddings.extend([[0.0] * self.EMBEDDING_DIM] * len(batch))
            
            # 4. 새로 생성한 임베딩 캐시에 저장
            await embedding_cache_service.set_batch_embeddings(
                texts_only,
                new_embeddings,
                self.MODEL_NAME
            )
            
            # 5. 결과에 추가
            for (idx, _), embedding in zip(texts_to_create, new_embeddings):
                result_embeddings.append((idx, embedding))
        
        # 6. 원래 순서로 정렬
        result_embeddings.sort(key=lambda x: x[0])
        final_embeddings = [emb for _, emb in result_embeddings]
        
        logger.info(f"배치 임베딩 생성 완료: {len(final_embeddings)}개")
        return final_embeddings
    
    async def create_chunk_embeddings(
        self,
        chunks: List[Chunk]
    ) -> List[Chunk]:
        """
        청크 리스트의 임베딩을 생성합니다.
        
        Args:
            chunks: Chunk 리스트
        
        Returns:
            임베딩이 추가된 Chunk 리스트
        """
        if not chunks:
            logger.warning("청크가 없습니다.")
            return []
        
        logger.info(f"청크 임베딩 생성 시작: {len(chunks)}개")
        
        # 텍스트 추출
        texts = [chunk.content for chunk in chunks]
        
        # 배치 임베딩 생성
        embeddings = await self.create_embeddings_batch(texts)
        
        # 청크에 임베딩 추가
        for chunk, embedding in zip(chunks, embeddings):
            chunk.metadata['embedding'] = embedding
            chunk.metadata['embedding_model'] = self.MODEL_NAME
            chunk.metadata['embedding_dim'] = len(embedding)
        
        logger.info(f"청크 임베딩 생성 완료: {len(chunks)}개")
        return chunks
    
    def validate_embedding(self, embedding: List[float]) -> bool:
        """
        임베딩 벡터의 유효성을 검증합니다.
        
        Args:
            embedding: 임베딩 벡터
        
        Returns:
            유효 여부
        """
        if not embedding:
            return False
        
        if len(embedding) != self.EMBEDDING_DIM:
            logger.error(
                f"임베딩 차원이 올바르지 않습니다: "
                f"{len(embedding)} != {self.EMBEDDING_DIM}"
            )
            return False
        
        # 제로 벡터 확인
        if all(v == 0.0 for v in embedding):
            logger.warning("제로 벡터가 감지되었습니다.")
            return False
        
        return True
    
    async def test_connection(self) -> bool:
        """
        OpenAI API 연결을 테스트합니다.
        
        Returns:
            연결 성공 여부
        """
        try:
            logger.info("OpenAI API 연결 테스트 중...")
            test_text = "테스트"
            embedding = await self.create_embedding(test_text)
            
            if self.validate_embedding(embedding):
                logger.info("✅ OpenAI API 연결 성공")
                return True
            else:
                logger.error("❌ 임베딩 검증 실패")
                return False
        
        except Exception as e:
            logger.error(f"❌ OpenAI API 연결 실패: {e}")
            return False

