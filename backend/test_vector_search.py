"""
벡터 검색 테스트 스크립트
호스피스 신청 관련 청크(1297, 1298)의 유사도를 확인합니다.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from services.vector_search import VectorSearchService
from core.config import settings


async def test_search():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        search_service = VectorSearchService()
        
        query = '호스피스의 신청은 어떻게?'
        
        # 검색 실행
        results = await search_service.search(
            session=session,
            query=query,
            threshold=0.3,  # 낮은 임계값으로 많은 결과 보기
            limit=50
        )
        
        print(f'\n=== 검색 쿼리: {query} ===')
        print(f'전체 결과 수: {len(results)}개\n')
        
        # document_id=32의 결과만 필터링
        doc32_results = [r for r in results if r.document_id == 32]
        print(f'Document 32 결과 수: {len(doc32_results)}개\n')
        
        print('=== Document 32 상위 20개 결과 ===')
        found_targets = {}
        
        for idx, result in enumerate(doc32_results[:20], 1):
            # chunk_id로 chunk_index 찾기
            ci = await session.execute(
                text('SELECT chunk_index FROM document_chunks WHERE id = :chunk_id'),
                {'chunk_id': result.chunk_id}
            )
            chunk_index = ci.scalar()
            
            is_target = ''
            if chunk_index in [1297, 1298]:
                is_target = ' ⭐ TARGET!'
                found_targets[chunk_index] = result.similarity
            
            print(f'{idx}. Chunk {chunk_index} - 유사도: {result.similarity:.4f}{is_target}')
            if idx <= 5 or is_target:
                print(f'   내용: {result.content[:100]}...')
        
        print(f'\n=== 결과 요약 ===')
        if 1297 in found_targets:
            print(f'✅ Chunk 1297 발견! 유사도: {found_targets[1297]:.4f}')
        else:
            print(f'❌ Chunk 1297 미발견 (상위 20개 밖)')
        
        if 1298 in found_targets:
            print(f'✅ Chunk 1298 발견! 유사도: {found_targets[1298]:.4f}')
        else:
            print(f'❌ Chunk 1298 미발견 (상위 20개 밖)')
    
    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(test_search())

