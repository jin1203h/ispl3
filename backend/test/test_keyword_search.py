"""
키워드 검색 기능 테스트
HybridSearchService.keyword_search() 메서드를 검증합니다.
"""
import asyncio
import sys
import os
from pathlib import Path

# backend 루트를 Python 경로에 추가
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

# 테스트 환경 설정
os.environ["TESTING"] = "true"

from sqlalchemy import text
from services.hybrid_search import HybridSearchService
from core.database import AsyncSessionLocal


async def test_keyword_search():
    """키워드 검색 통합 테스트"""
    print("=" * 60)
    print("키워드 검색 테스트 시작")
    print("=" * 60)
    
    # 서비스 초기화
    hybrid_service = HybridSearchService()
    session = AsyncSessionLocal()
    
    try:
        # 1. 데이터 존재 여부 확인
        print("\n1️⃣ 데이터 존재 여부 확인...")
        chunk_count = await session.execute(text("SELECT COUNT(*) FROM document_chunks"))
        total_chunks = chunk_count.scalar()
        print(f"   - 총 청크 수: {total_chunks}")
        
        if total_chunks == 0:
            print("   ⚠️  청크 데이터가 없습니다. 테스트를 건너뜁니다.")
            return
        
        # content_tsv가 있는 청크 수 확인
        tsv_count = await session.execute(
            text("SELECT COUNT(*) FROM document_chunks WHERE content_tsv IS NOT NULL")
        )
        tsv_chunks = tsv_count.scalar()
        print(f"   - content_tsv 있는 청크: {tsv_chunks}")
        
        if tsv_chunks == 0:
            print("\n   📝 테스트를 위해 일부 청크에 content_tsv 생성...")
            # 처음 10개 청크에 content_tsv 생성
            await session.execute(text("""
                UPDATE document_chunks 
                SET content_tsv = to_tsvector('simple', content)
                WHERE id IN (SELECT id FROM document_chunks LIMIT 10)
            """))
            await session.commit()
            print("   ✓ 10개 청크에 content_tsv 생성 완료")
        
        # 2. 쿼리 전처리 테스트
        print("\n2️⃣ 쿼리 전처리 테스트...")
        test_queries = [
            "암 진단비",
            "보험!!!금액???",
            "   여러   공백   ",
            "",
            "제15조"
        ]
        
        for q in test_queries:
            preprocessed = hybrid_service._preprocess_query(q)
            tsquery = hybrid_service._build_tsquery(preprocessed)
            print(f"   '{q}' → '{preprocessed}' → tsquery: '{tsquery}'")
        
        # 3. 키워드 검색 테스트
        print("\n3️⃣ 키워드 검색 실행...")
        
        # 3-1. 일반 검색
        print("\n   [테스트 3-1] 일반 키워드 검색")
        results = await hybrid_service.keyword_search(
            session=session,
            query="보험",
            limit=5
        )
        print(f"   ✓ '보험' 검색 결과: {len(results)}개")
        if results:
            print(f"   ✓ 최고 점수: {results[0].similarity:.4f}")
            print(f"   ✓ 첫 번째 결과: {results[0].content[:100]}...")
        
        # 3-2. 복합 키워드 검색
        print("\n   [테스트 3-2] 복합 키워드 검색")
        results = await hybrid_service.keyword_search(
            session=session,
            query="진단 보험",
            limit=5
        )
        print(f"   ✓ '진단 보험' 검색 결과: {len(results)}개")
        if results:
            print(f"   ✓ 최고 점수: {results[0].similarity:.4f}")
        
        # 3-3. 빈 쿼리
        print("\n   [테스트 3-3] 빈 쿼리")
        results = await hybrid_service.keyword_search(
            session=session,
            query="",
            limit=5
        )
        print(f"   ✓ 빈 쿼리 결과: {len(results)}개 (예상: 0개)")
        assert len(results) == 0, "빈 쿼리는 빈 결과를 반환해야 함"
        
        # 3-4. 특수문자만
        print("\n   [테스트 3-4] 특수문자만")
        results = await hybrid_service.keyword_search(
            session=session,
            query="!!!???",
            limit=5
        )
        print(f"   ✓ 특수문자만 결과: {len(results)}개 (예상: 0개)")
        assert len(results) == 0, "특수문자만 있는 쿼리는 빈 결과를 반환해야 함"
        
        # 3-5. 존재하지 않는 키워드
        print("\n   [테스트 3-5] 존재하지 않는 키워드")
        results = await hybrid_service.keyword_search(
            session=session,
            query="존재하지않는키워드xyz123",
            limit=5
        )
        print(f"   ✓ 존재하지 않는 키워드 결과: {len(results)}개")
        
        # 4. VectorSearchResult 형식 검증
        print("\n4️⃣ VectorSearchResult 형식 검증...")
        results = await hybrid_service.keyword_search(
            session=session,
            query="보험",
            limit=1
        )
        
        if results:
            result = results[0]
            print(f"   ✓ chunk_id: {result.chunk_id}")
            print(f"   ✓ similarity: {result.similarity}")
            print(f"   ✓ content: {result.content[:50]}...")
            print(f"   ✓ document_filename: {result.document_filename}")
            
            # to_dict() 메서드 테스트
            result_dict = result.to_dict()
            assert "chunk_id" in result_dict, "to_dict() 실패"
            assert "similarity" in result_dict, "similarity 필드 누락"
            print(f"   ✓ to_dict() 정상 작동")
        
        print("\n" + "=" * 60)
        print("✅ 모든 테스트 통과!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(test_keyword_search())

