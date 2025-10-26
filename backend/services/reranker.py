"""
검색 결과 Re-ranking 서비스

검색 결과의 순위를 재조정하여 정확한 매칭을 상위로 올립니다.
Lost in the Middle 문제를 해결하기 위해 사용합니다.
"""
import logging
from typing import List, Dict, Any
from utils.text_utils import extract_keywords

logger = logging.getLogger(__name__)


class RerankerService:
    """검색 결과 순위 재조정 서비스"""
    
    # 점수 가중치
    EXACT_MATCH_WEIGHT = 0.3  # 정확한 키워드 매칭 가중치
    PARTIAL_MATCH_WEIGHT = 0.1  # 부분 매칭 가중치
    POSITION_BONUS_WEIGHT = 0.05  # 위치 보너스 (앞부분에 있으면 가산)
    
    def __init__(self):
        """RerankerService 초기화"""
        logger.info("RerankerService 초기화 완료")
    
    def calculate_exact_match_score(
        self,
        content: str,
        keywords: List[str]
    ) -> float:
        """
        콘텐츠에서 키워드 정확 매칭 점수 계산
        
        Args:
            content: 청크 내용
            keywords: 검색 키워드 리스트
        
        Returns:
            매칭 점수 (0.0 ~ 1.0)
        """
        if not keywords or not content:
            return 0.0
        
        content_lower = content.lower()
        
        # 콘텐츠 앞부분 (처음 200자)
        content_front = content[:200].lower()
        
        exact_matches = 0
        partial_matches = 0
        front_matches = 0
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # 1. 정확한 매칭 (대소문자 무시)
            if keyword_lower in content_lower:
                exact_matches += 1
                
                # 2. 앞부분에 있으면 보너스
                if keyword_lower in content_front:
                    front_matches += 1
            else:
                # 3. 부분 매칭 (키워드의 일부라도 있는지)
                # 예: "초간편고지" → "간편", "고지" 중 하나라도
                if len(keyword) >= 4:
                    # 긴 키워드는 반으로 나눠서 체크
                    mid = len(keyword) // 2
                    part1 = keyword_lower[:mid]
                    part2 = keyword_lower[mid:]
                    
                    if part1 in content_lower or part2 in content_lower:
                        partial_matches += 0.5
        
        # 점수 계산
        total_keywords = len(keywords)
        exact_ratio = exact_matches / total_keywords
        partial_ratio = partial_matches / total_keywords
        front_ratio = front_matches / total_keywords if exact_matches > 0 else 0
        
        # 가중 평균
        score = (
            exact_ratio * self.EXACT_MATCH_WEIGHT +
            partial_ratio * self.PARTIAL_MATCH_WEIGHT +
            front_ratio * self.POSITION_BONUS_WEIGHT
        )
        
        logger.debug(
            f"매칭 점수: exact={exact_matches}/{total_keywords}, "
            f"partial={partial_matches:.1f}/{total_keywords}, "
            f"front={front_matches}/{total_keywords}, "
            f"score={score:.4f}"
        )
        
        return score
    
    def rerank(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        keywords: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        검색 결과를 재정렬합니다.
        
        정확한 키워드 매칭을 기준으로 점수를 재계산하고,
        기존 유사도 점수와 결합하여 최종 순위를 결정합니다.
        
        Args:
            query: 원본 질의
            search_results: 검색 결과 리스트 (딕셔너리)
            keywords: 추출된 키워드 (없으면 자동 추출)
        
        Returns:
            재정렬된 검색 결과 리스트
        """
        if not search_results:
            return search_results
        
        # 키워드 추출 (제공되지 않은 경우)
        if keywords is None:
            keywords = extract_keywords(query)
        
        logger.info(
            f"Re-ranking 시작: {len(search_results)}개 결과, "
            f"키워드={keywords}"
        )
        
        # 각 결과에 대해 정확도 점수 계산
        reranked_results = []
        
        for idx, result in enumerate(search_results):
            content = result.get('content', '')
            original_similarity = result.get('similarity', 0.0)
            
            # 정확 매칭 점수 계산
            exact_score = self.calculate_exact_match_score(content, keywords)
            
            # 최종 점수 = 원래 유사도 + 정확도 보너스
            final_score = original_similarity + exact_score
            
            # 결과에 추가 정보 저장
            result_copy = result.copy()
            result_copy['rerank_exact_score'] = exact_score
            result_copy['rerank_final_score'] = final_score
            result_copy['original_rank'] = idx + 1  # 원래 순위 보존
            
            reranked_results.append(result_copy)
            
            logger.debug(
                f"[{idx+1}] chunk_id={result.get('chunk_id')}, "
                f"similarity={original_similarity:.4f}, "
                f"exact={exact_score:.4f}, "
                f"final={final_score:.4f}"
            )
        
        # 최종 점수로 재정렬 (높은 순)
        reranked_results.sort(
            key=lambda x: x['rerank_final_score'],
            reverse=True
        )
        
        # 로그 출력
        logger.info("Re-ranking 완료:")
        for idx, result in enumerate(reranked_results[:5]):  # 상위 5개만
            logger.info(
                f"  [{idx+1}] chunk_id={result.get('chunk_id')} "
                f"(원래: {result['original_rank']}위) "
                f"final_score={result['rerank_final_score']:.4f} "
                f"(similarity={result.get('similarity'):.4f} + "
                f"exact={result['rerank_exact_score']:.4f})"
            )
        
        return reranked_results


# 전역 인스턴스
reranker_service = RerankerService()

