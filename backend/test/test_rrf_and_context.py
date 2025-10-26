"""
RRF 융합 및 컨텍스트 최적화 테스트
HybridSearchService의 RRF와 토큰 제한 기능을 검증합니다.
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

from services.hybrid_search import HybridSearchService
from services.vector_search import VectorSearchResult


def create_mock_result(chunk_id: int, content: str, similarity: float) -> VectorSearchResult:
    """테스트용 VectorSearchResult 생성"""
    return VectorSearchResult(
        chunk_id=chunk_id,
        document_id=1,
        content=content,
        similarity=similarity,
        chunk_type="text",
        document_filename="test.pdf"
    )


def test_reciprocal_rank_fusion():
    """RRF 알고리즘 테스트"""
    print("=" * 60)
    print("RRF (Reciprocal Rank Fusion) 테스트")
    print("=" * 60)
    
    hybrid_service = HybridSearchService()
    
    # 테스트 데이터 생성
    vector_results = [
        create_mock_result(1, "벡터 1위", 0.9),
        create_mock_result(2, "벡터 2위", 0.8),
        create_mock_result(3, "벡터 3위", 0.7),
    ]
    
    keyword_results = [
        create_mock_result(2, "키워드 1위", 0.95),  # chunk_id=2 (중복)
        create_mock_result(4, "키워드 2위", 0.85),
        create_mock_result(5, "키워드 3위", 0.75),
    ]
    
    print(f"\n벡터 검색 결과: {len(vector_results)}개")
    for i, r in enumerate(vector_results):
        print(f"  {i+1}위: chunk_id={r.chunk_id}, similarity={r.similarity}")
    
    print(f"\n키워드 검색 결과: {len(keyword_results)}개")
    for i, r in enumerate(keyword_results):
        print(f"  {i+1}위: chunk_id={r.chunk_id}, similarity={r.similarity}")
    
    # RRF 융합
    print("\n🔄 RRF 융합 실행...")
    fused_results = hybrid_service.reciprocal_rank_fusion(
        vector_results=vector_results,
        keyword_results=keyword_results,
        k=60
    )
    
    print(f"\n융합 결과: {len(fused_results)}개")
    for i, (chunk_id, score) in enumerate(fused_results[:10]):
        print(f"  {i+1}위: chunk_id={chunk_id}, rrf_score={score:.6f}")
    
    # 검증
    print("\n✅ 검증:")
    
    # 1. chunk_id 중복 없음
    chunk_ids = [chunk_id for chunk_id, _ in fused_results]
    assert len(chunk_ids) == len(set(chunk_ids)), "chunk_id 중복 발견!"
    print("  ✓ chunk_id 중복 없음")
    
    # 2. 점수 내림차순 정렬
    scores = [score for _, score in fused_results]
    assert scores == sorted(scores, reverse=True), "점수가 내림차순으로 정렬되지 않음!"
    print("  ✓ 점수 내림차순 정렬")
    
    # 3. chunk_id=2는 양쪽에 모두 있으므로 높은 점수
    chunk_2_score = next(score for cid, score in fused_results if cid == 2)
    chunk_1_score = next(score for cid, score in fused_results if cid == 1)
    assert chunk_2_score > chunk_1_score, "중복된 chunk_id=2의 점수가 더 높아야 함!"
    print(f"  ✓ chunk_id=2 점수 ({chunk_2_score:.6f}) > chunk_id=1 점수 ({chunk_1_score:.6f})")
    
    # 4. RRF 점수 계산 검증
    # chunk_id=1: 벡터 1위 → 1/(60+0+1) = 0.01639
    expected_score_1 = 1.0 / (60 + 0 + 1)
    assert abs(chunk_1_score - expected_score_1) < 0.0001, "RRF 점수 계산 오류!"
    print(f"  ✓ RRF 점수 계산 정확: {chunk_1_score:.6f} ≈ {expected_score_1:.6f}")
    
    # chunk_id=2: 벡터 2위 + 키워드 1위
    # → 1/(60+1+1) + 1/(60+0+1) = 0.01613 + 0.01639 = 0.03252
    expected_score_2 = 1.0 / (60 + 1 + 1) + 1.0 / (60 + 0 + 1)
    assert abs(chunk_2_score - expected_score_2) < 0.0001, "RRF 점수 계산 오류!"
    print(f"  ✓ RRF 점수 계산 정확: {chunk_2_score:.6f} ≈ {expected_score_2:.6f}")
    
    print("\n✅ RRF 테스트 통과!")


def test_optimize_context():
    """컨텍스트 최적화 테스트"""
    print("\n" + "=" * 60)
    print("컨텍스트 최적화 (토큰 제한) 테스트")
    print("=" * 60)
    
    hybrid_service = HybridSearchService()
    
    # 테스트 데이터 생성 (다양한 길이의 텍스트)
    search_results = [
        create_mock_result(1, "짧은 텍스트", 0.9),
        create_mock_result(2, "조금 더 긴 텍스트입니다.", 0.8),
        create_mock_result(3, "훨씬 더 긴 텍스트입니다. " * 100, 0.7),  # 매우 긴 텍스트
        create_mock_result(4, "또 다른 텍스트", 0.6),
        create_mock_result(5, "마지막 텍스트", 0.5),
    ]
    
    print(f"\n검색 결과: {len(search_results)}개")
    for i, r in enumerate(search_results):
        tokens = len(hybrid_service.encoding.encode(r.content))
        print(f"  {i+1}. chunk_id={r.chunk_id}, tokens={tokens}, content_len={len(r.content)}")
    
    # 1. 낮은 토큰 제한 (100 토큰)
    print("\n🔄 컨텍스트 최적화 (제한: 100 토큰)...")
    optimized, total_tokens = hybrid_service.optimize_context(
        search_results=search_results,
        max_tokens=100
    )
    
    print(f"  ✓ 최적화 결과: {len(optimized)}/{len(search_results)}개 청크")
    print(f"  ✓ 총 토큰: {total_tokens} (제한: 100)")
    
    # 검증
    assert total_tokens <= 100, "토큰 제한 초과!"
    assert len(optimized) < len(search_results), "일부 청크가 제외되어야 함!"
    print("  ✓ 토큰 제한 준수")
    
    # 2. 높은 토큰 제한 (8000 토큰)
    print("\n🔄 컨텍스트 최적화 (제한: 8000 토큰)...")
    optimized, total_tokens = hybrid_service.optimize_context(
        search_results=search_results,
        max_tokens=8000
    )
    
    print(f"  ✓ 최적화 결과: {len(optimized)}/{len(search_results)}개 청크")
    print(f"  ✓ 총 토큰: {total_tokens} (제한: 8000)")
    
    assert total_tokens <= 8000, "토큰 제한 초과!"
    print("  ✓ 토큰 제한 준수")
    
    # 3. 빈 결과
    print("\n🔄 컨텍스트 최적화 (빈 결과)...")
    optimized, total_tokens = hybrid_service.optimize_context(
        search_results=[],
        max_tokens=8000
    )
    
    assert len(optimized) == 0, "빈 결과는 빈 리스트를 반환해야 함!"
    assert total_tokens == 0, "빈 결과의 토큰 수는 0이어야 함!"
    print("  ✓ 빈 결과 처리 정상")
    
    # 4. 기본 제한 (8000 토큰)
    print("\n🔄 컨텍스트 최적화 (기본 제한)...")
    optimized, total_tokens = hybrid_service.optimize_context(
        search_results=search_results
    )
    
    assert total_tokens <= 8000, "기본 제한 초과!"
    print(f"  ✓ 기본 제한 적용: {total_tokens} <= 8000")
    
    print("\n✅ 컨텍스트 최적화 테스트 통과!")


def test_rrf_edge_cases():
    """RRF 엣지 케이스 테스트"""
    print("\n" + "=" * 60)
    print("RRF 엣지 케이스 테스트")
    print("=" * 60)
    
    hybrid_service = HybridSearchService()
    
    # 1. 벡터 검색만 있는 경우
    print("\n[케이스 1] 벡터 검색만")
    vector_only = [
        create_mock_result(1, "벡터 1", 0.9),
        create_mock_result(2, "벡터 2", 0.8),
    ]
    fused = hybrid_service.reciprocal_rank_fusion(vector_only, [])
    assert len(fused) == 2, "벡터 검색만 있는 경우 결과 수가 맞지 않음!"
    print(f"  ✓ 결과: {len(fused)}개 (예상: 2)")
    
    # 2. 키워드 검색만 있는 경우
    print("\n[케이스 2] 키워드 검색만")
    keyword_only = [
        create_mock_result(3, "키워드 1", 0.95),
        create_mock_result(4, "키워드 2", 0.85),
    ]
    fused = hybrid_service.reciprocal_rank_fusion([], keyword_only)
    assert len(fused) == 2, "키워드 검색만 있는 경우 결과 수가 맞지 않음!"
    print(f"  ✓ 결과: {len(fused)}개 (예상: 2)")
    
    # 3. 둘 다 빈 경우
    print("\n[케이스 3] 둘 다 빈 결과")
    fused = hybrid_service.reciprocal_rank_fusion([], [])
    assert len(fused) == 0, "빈 결과는 빈 리스트를 반환해야 함!"
    print(f"  ✓ 결과: {len(fused)}개 (예상: 0)")
    
    # 4. 완전히 동일한 chunk_id
    print("\n[케이스 4] 완전히 동일한 chunk_id")
    same_ids_v = [create_mock_result(1, "동일1", 0.9)]
    same_ids_k = [create_mock_result(1, "동일1", 0.9)]
    fused = hybrid_service.reciprocal_rank_fusion(same_ids_v, same_ids_k)
    assert len(fused) == 1, "중복된 chunk_id는 하나로 통합되어야 함!"
    score = fused[0][1]
    expected = 1.0/(60+0+1) + 1.0/(60+0+1)  # 양쪽 1위
    assert abs(score - expected) < 0.0001, "중복 chunk_id의 점수가 합산되어야 함!"
    print(f"  ✓ 중복 chunk_id 통합: {score:.6f} ≈ {expected:.6f}")
    
    print("\n✅ 엣지 케이스 테스트 통과!")


if __name__ == "__main__":
    try:
        test_reciprocal_rank_fusion()
        test_optimize_context()
        test_rrf_edge_cases()
        
        print("\n" + "=" * 60)
        print("🎉 모든 테스트 통과!")
        print("=" * 60)
    
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

