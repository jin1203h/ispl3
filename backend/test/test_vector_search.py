"""
벡터 검색 테스트
벡터 검색 서비스와 API의 기능을 테스트합니다.
"""
import sys
import os
from pathlib import Path

# 테스트 환경 설정 (모듈 import 전에 설정)
os.environ["TESTING"] = "true"

# backend 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import AsyncSessionLocal
from services.vector_search import VectorSearchService
from models.document_chunk import DocumentChunk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_vector_search():
    """벡터 검색 테스트"""
    async with AsyncSessionLocal() as session:
        try:
            logger.info("=" * 80)
            logger.info("벡터 검색 테스트 시작")
            logger.info("=" * 80)
            
            # 1. 검색 서비스 초기화
            search_service = VectorSearchService()
            
            # 2. 저장된 청크 수 확인
            result = await session.execute(select(DocumentChunk))
            chunks = result.scalars().all()
            chunk_count = len(chunks)
            
            logger.info(f"\n✅ 저장된 청크 수: {chunk_count}개")
            
            if chunk_count == 0:
                logger.warning("⚠️  검색할 청크가 없습니다. PDF를 먼저 업로드하세요.")
                return
            
            # 3. 샘플 청크 확인
            sample_chunk = chunks[0]
            # 세션이 닫히기 전에 필요한 값을 미리 가져옴
            sample_chunk_id = sample_chunk.id
            sample_chunk_content = sample_chunk.content
            
            logger.info(f"\n📄 샘플 청크 정보:")
            logger.info(f"  - ID: {sample_chunk.id}")
            logger.info(f"  - 문서 ID: {sample_chunk.document_id}")
            logger.info(f"  - 타입: {sample_chunk.chunk_type}")
            logger.info(f"  - 내용 (앞 100자): {sample_chunk.content[:100]}...")
            logger.info(f"  - 페이지: {sample_chunk.page_number}")
            logger.info(f"  - 조항 번호: {sample_chunk.clause_number}")
            
            # 4. 테스트 쿼리 목록
            test_queries = [
                "골절 시 보장 여부는 어떻게 되나요?",
                "보험료 납입 방법에 대해 알려주세요",
                "계약 해지 시 환급금은 어떻게 되나요?",
                "보험금 청구 절차를 알려주세요"
            ]
            
            # 5. 각 쿼리로 검색 테스트
            for i, query in enumerate(test_queries, 1):
                logger.info("\n" + "=" * 80)
                logger.info(f"테스트 쿼리 {i}/{len(test_queries)}: {query}")
                logger.info("=" * 80)
                
                # 벡터 검색 수행
                results = await search_service.search(
                    session=session,
                    query=query,
                    threshold=0.7,
                    limit=5
                )
                
                if results:
                    logger.info(f"\n✅ 검색 결과: {len(results)}개")
                    for j, result in enumerate(results, 1):
                        logger.info(f"\n--- 결과 {j} ---")
                        logger.info(f"유사도: {result.similarity:.3f}")
                        logger.info(f"문서: {result.document_filename}")
                        logger.info(f"페이지: {result.page_number}")
                        logger.info(f"조항: {result.clause_number or 'N/A'}")
                        logger.info(f"타입: {result.chunk_type}")
                        logger.info(f"내용 (앞 200자):")
                        logger.info(f"{result.content[:200]}...")
                else:
                    logger.warning(f"⚠️  '{query}'에 대한 검색 결과가 없습니다.")
                
                # API 응답 시간을 고려하여 잠시 대기
                await asyncio.sleep(1)
            
            # 6. 유사 청크 검색 테스트
            logger.info("\n" + "=" * 80)
            logger.info("유사 청크 검색 테스트")
            logger.info("=" * 80)
            
            logger.info(f"\n기준 청크 ID: {sample_chunk_id}")
            logger.info(f"기준 청크 내용 (앞 100자): {sample_chunk_content[:100]}...")
            
            similar_chunks = await search_service.get_similar_chunks(
                session=session,
                chunk_id=sample_chunk_id,
                limit=3
            )
            
            if similar_chunks:
                logger.info(f"\n✅ 유사 청크: {len(similar_chunks)}개")
                for j, result in enumerate(similar_chunks, 1):
                    logger.info(f"\n--- 유사 청크 {j} ---")
                    logger.info(f"청크 ID: {result.chunk_id}")
                    logger.info(f"유사도: {result.similarity:.3f}")
                    logger.info(f"문서: {result.document_filename}")
                    logger.info(f"내용 (앞 100자):")
                    logger.info(f"{result.content[:100]}...")
            else:
                logger.warning("⚠️  유사한 청크를 찾을 수 없습니다.")
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ 벡터 검색 테스트 완료")
            logger.info("=" * 80)
        
        except Exception as e:
            logger.error(f"❌ 테스트 중 오류 발생: {e}", exc_info=True)
        
        finally:
            await session.close()


async def test_search_with_filters():
    """필터링 검색 테스트"""
    async with AsyncSessionLocal() as session:
        try:
            logger.info("\n" + "=" * 80)
            logger.info("필터링 검색 테스트")
            logger.info("=" * 80)
            
            search_service = VectorSearchService()
            
            # 문서 타입별 검색
            query = "보험금 청구"
            document_types = ["policy", "clause", "faq"]
            
            for doc_type in document_types:
                logger.info(f"\n--- 문서 타입: {doc_type} ---")
                results = await search_service.search(
                    session=session,
                    query=query,
                    document_type=doc_type,
                    threshold=0.7,
                    limit=3
                )
                logger.info(f"검색 결과: {len(results)}개")
            
            logger.info("\n✅ 필터링 검색 테스트 완료")
        
        except Exception as e:
            logger.error(f"❌ 필터링 검색 테스트 실패: {e}")
        
        finally:
            await session.close()


if __name__ == "__main__":
    # 기본 벡터 검색 테스트
    asyncio.run(test_vector_search())
    
    # 필터링 검색 테스트
    # asyncio.run(test_search_with_filters())

