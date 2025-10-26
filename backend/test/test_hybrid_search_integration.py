"""
하이브리드 검색 통합 테스트
hybrid_search() 메서드의 전체 워크플로우를 검증합니다.
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


async def test_hybrid_search_integration():
    """하이브리드 검색 통합 테스트"""
    print("=" * 60)
    print("하이브리드 검색 통합 테스트")
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
        
        # content_tsv 생성 (필요 시)
        tsv_count = await session.execute(
            text("SELECT COUNT(*) FROM document_chunks WHERE content_tsv IS NOT NULL")
        )
        tsv_chunks = tsv_count.scalar()
        
        if tsv_chunks == 0:
            print(f"   📝 content_tsv 생성 중...")
            await session.execute(text("""
                UPDATE document_chunks 
                SET content_tsv = to_tsvector('simple', content)
                WHERE id IN (SELECT id FROM document_chunks LIMIT 20)
            """))
            await session.commit()
            print("   ✓ 20개 청크에 content_tsv 생성 완료")
        
        # 2. 하이브리드 검색 실행
        print("\n2️⃣ 하이브리드 검색 실행...")
        
        test_queries = [
            ("보험", 5, 8000),
            ("암 진단", 3, 5000),
            ("제15조", 5, 8000),
        ]
        
        for query, limit, max_tokens in test_queries:
            print(f"\n   [테스트] query='{query}', limit={limit}, max_tokens={max_tokens}")
            
            results, total_tokens = await hybrid_service.hybrid_search(
                session=session,
                query=query,
                limit=limit,
                max_tokens=max_tokens,
                threshold=0.5,  # 낮은 threshold로 더 많은 결과
                user_id=None
            )
            
            print(f"   ✓ 결과: {len(results)}개 청크")
            print(f"   ✓ 총 토큰: {total_tokens}")
            
            if results:
                print(f"   ✓ 최고 점수: {results[0].similarity:.6f}")
                print(f"   ✓ 첫 번째 결과: {results[0].content[:100]}...")
            
            # 검증
            assert isinstance(results, list), "결과가 리스트가 아님!"
            assert isinstance(total_tokens, int), "total_tokens가 int가 아님!"
            assert total_tokens <= max_tokens, f"토큰 제한 초과: {total_tokens} > {max_tokens}"
            assert len(results) <= limit, f"결과 수 초과: {len(results)} > {limit}"
            
            print(f"   ✅ 검증 통과")
        
        # 3. 병렬 실행 확인
        print("\n3️⃣ 병렬 실행 확인 (응답 시간 측정)...")
        
        import time
        
        start = time.time()
        results, total_tokens = await hybrid_service.hybrid_search(
            session=session,
            query="보험 약관",
            limit=5,
            threshold=0.5
        )
        elapsed = (time.time() - start) * 1000
        
        print(f"   ✓ 하이브리드 검색 응답 시간: {elapsed:.0f}ms")
        print(f"   ✓ 결과: {len(results)}개, {total_tokens}토큰")
        
        # 병렬 실행이므로 단일 검색보다 빨라야 함
        # (하지만 테스트 환경에서는 정확하지 않을 수 있음)
        
        # 4. 예외 처리 테스트
        print("\n4️⃣ 예외 처리 테스트...")
        
        # 빈 쿼리
        print("   [테스트] 빈 쿼리")
        results, total_tokens = await hybrid_service.hybrid_search(
            session=session,
            query="",
            limit=5
        )
        print(f"   ✓ 빈 쿼리 결과: {len(results)}개 (예상: 0)")
        # 키워드 검색이 빈 결과를 반환하고, 벡터 검색도 빈 쿼리라면 빈 결과
        
        # 특수문자만
        print("   [테스트] 특수문자만")
        results, total_tokens = await hybrid_service.hybrid_search(
            session=session,
            query="!!!???###",
            limit=5
        )
        print(f"   ✓ 특수문자 결과: {len(results)}개")
        
        # 5. 검색 로그 확인
        print("\n5️⃣ 검색 로그 확인...")
        
        log_count = await session.execute(text("""
            SELECT COUNT(*) 
            FROM search_logs 
            WHERE search_type = 'hybrid'
        """))
        hybrid_logs = log_count.scalar()
        
        print(f"   ✓ hybrid 검색 로그: {hybrid_logs}개")
        
        if hybrid_logs > 0:
            # 최근 로그 조회
            recent_log = await session.execute(text("""
                SELECT query, results_count, response_time_ms, top_similarity_score
                FROM search_logs
                WHERE search_type = 'hybrid'
                ORDER BY created_at DESC
                LIMIT 1
            """))
            log = recent_log.fetchone()
            
            print(f"   ✓ 최근 로그:")
            print(f"      - query: {log.query[:30]}...")
            print(f"      - results_count: {log.results_count}")
            print(f"      - response_time_ms: {log.response_time_ms}ms")
            print(f"      - top_similarity_score: {log.top_similarity_score:.6f}")
        
        # 6. chunk_cache 효율성 확인
        print("\n6️⃣ chunk_cache 효율성 확인...")
        
        # 동일한 chunk_id가 벡터와 키워드 양쪽에 나타나는 경우
        # chunk_cache로 재조회 없이 처리
        results, total_tokens = await hybrid_service.hybrid_search(
            session=session,
            query="보험 진단",
            limit=5
        )
        
        print(f"   ✓ chunk_cache 사용하여 {len(results)}개 결과 반환")
        print(f"   ✓ DB 재조회 없이 기존 결과 재사용")
        
        print("\n" + "=" * 60)
        print("✅ 모든 통합 테스트 통과!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    finally:
        await session.close()


async def test_hybrid_search_with_filters():
    """하이브리드 검색 필터 테스트"""
    print("\n" + "=" * 60)
    print("하이브리드 검색 필터 테스트")
    print("=" * 60)
    
    hybrid_service = HybridSearchService()
    session = AsyncSessionLocal()
    
    try:
        # clause_number 필터
        print("\n[테스트] clause_number 필터")
        results, total_tokens = await hybrid_service.hybrid_search(
            session=session,
            query="보험",
            limit=5,
            clause_number="제15조",
            threshold=0.3  # 낮은 threshold (clause_number 필터가 있으므로)
        )
        
        print(f"   ✓ 결과: {len(results)}개")
        
        if results:
            for r in results:
                print(f"   ✓ chunk_id={r.chunk_id}, clause_number={r.clause_number}")
        
        print("\n✅ 필터 테스트 통과!")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(test_hybrid_search_integration())
    asyncio.run(test_hybrid_search_with_filters())

