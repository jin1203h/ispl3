"""
하이브리드 검색 서비스
벡터 검색과 키워드 검색을 결합하여 더 정확한 검색 결과를 제공합니다.
"""
import re
import logging
import asyncio
import time
from typing import List, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import tiktoken

from services.vector_search import VectorSearchService, VectorSearchResult
from utils.text_utils import extract_keywords

logger = logging.getLogger(__name__)


class HybridSearchService:
    """
    하이브리드 검색 서비스
    
    벡터 검색(의미 기반)과 키워드 검색(정확한 매칭)을 결합하여
    더 높은 검색 정확도를 제공합니다.
    
    Reciprocal Rank Fusion (RRF) 알고리즘으로 검색 결과를 융합하고,
    컨텍스트 최적화로 LLM 토큰 제한을 적용합니다.
    """
    
    # RRF 파라미터 (표준값)
    RRF_K = 60
    
    # 컨텍스트 토큰 제한 (GPT-4o 기준 - 128K 컨텍스트)
    MAX_CONTEXT_TOKENS = 20000  # gpt-4o 변경으로 8000 → 20000 증가
    
    def __init__(self):
        """하이브리드 검색 서비스 초기화"""
        self.vector_search_service = VectorSearchService()
        # GPT-4 호환 인코딩
        self.encoding = tiktoken.get_encoding("cl100k_base")
        logger.info(
            f"HybridSearchService 초기화 완료: "
            f"RRF_K={self.RRF_K}, MAX_TOKENS={self.MAX_CONTEXT_TOKENS}"
        )
    
    def _preprocess_query(self, query: str) -> str:
        """
        검색 쿼리를 전처리합니다.
        
        특수문자를 제거하고 공백을 정리하여 Full-Text Search에 적합한 형태로 변환합니다.
        
        Args:
            query: 원본 검색 쿼리
        
        Returns:
            전처리된 쿼리 문자열
        """
        # 특수문자 제거 (한글, 영문, 숫자, 공백만 유지)
        clean_query = re.sub(r'[^\w\s가-힣]', ' ', query)
        
        # 연속된 공백을 하나로 치환
        clean_query = re.sub(r'\s+', ' ', clean_query).strip()
        
        return clean_query
    
    def _build_tsquery(self, query: str) -> Optional[str]:
        """
        PostgreSQL tsquery 문자열을 생성합니다.
        
        띄어쓰기로 구분된 단어들에서 조사를 제거하고 & 연산자로 연결합니다.
        (AND 검색: 모든 단어가 포함된 문서 검색)
        
        Args:
            query: 전처리된 검색 쿼리
        
        Returns:
            tsquery 문자열 또는 None (빈 쿼리인 경우)
        """
        # 공통 유틸리티 함수 사용
        keywords = extract_keywords(query)
        
        if not keywords:
            return None
        
        # 각 단어를 tsquery 형식으로 변환
        # 예: "호스피스의 신청은" → "호스피스 & 신청"
        tsquery = ' & '.join(keywords)
        
        logger.debug(f"tsquery 생성: '{query}' → '{tsquery}'")
        
        return tsquery
    
    async def keyword_search(
        self,
        session: AsyncSession,
        query: str,
        limit: int = 10,
        document_type: Optional[str] = None,
        clause_number: Optional[str] = None
    ) -> List[VectorSearchResult]:
        """
        PostgreSQL Full-Text Search를 사용한 키워드 검색
        
        Args:
            session: 데이터베이스 세션
            query: 검색 쿼리
            limit: 최대 결과 수 (기본: 10)
            document_type: 문서 타입 필터 (선택사항)
            clause_number: 조항 번호 필터 (선택사항)
        
        Returns:
            VectorSearchResult 리스트 (ts_rank를 similarity로 매핑)
        """
        logger.info(f"키워드 검색 시작: query='{query[:50]}...', limit={limit}")
        
        # 1. 쿼리 전처리
        clean_query = self._preprocess_query(query)
        
        if not clean_query:
            logger.warning("전처리 후 빈 쿼리: 빈 결과 반환")
            return []
        
        # 2. tsquery 생성
        tsquery = self._build_tsquery(clean_query)
        
        if not tsquery:
            logger.warning("tsquery 생성 실패: 빈 결과 반환")
            return []
        
        # 3. 필터 조건 구성
        document_filter = ""
        if document_type:
            document_filter = "AND d.document_type = :document_type"
        
        clause_filter = ""
        if clause_number:
            clause_filter = "AND c.clause_number = :clause_number"
            logger.info(f"조항 번호 필터 적용: {clause_number}")
        
        # 4. Full-Text Search 쿼리 실행
        query_sql = text(f"""
            SELECT 
                c.id as chunk_id,
                c.document_id,
                c.content,
                c.chunk_type,
                c.page_number,
                c.section_title,
                c.clause_number,
                c.metadata,
                c.token_count,
                d.filename as document_filename,
                d.document_type,
                d.company_name,
                ts_rank(c.content_tsv, to_tsquery('simple', :tsquery)) as rank
            FROM document_chunks c
            INNER JOIN documents d ON c.document_id = d.id
            WHERE c.content_tsv @@ to_tsquery('simple', :tsquery)
                AND d.status = 'active'
                {document_filter}
                {clause_filter}
            ORDER BY rank DESC
            LIMIT :limit
        """)
        
        # 5. 파라미터 바인딩
        params = {
            "tsquery": tsquery,
            "limit": limit
        }
        
        if document_type:
            params["document_type"] = document_type
        
        if clause_number:
            params["clause_number"] = clause_number
        
        try:
            # 6. 쿼리 실행
            result = await session.execute(query_sql, params)
            rows = result.fetchall()
            
            logger.info(f"키워드 검색 완료: {len(rows)}개 결과")
            
            # 7. VectorSearchResult로 변환
            search_results = []
            for row in rows:
                search_result = VectorSearchResult(
                    chunk_id=row.chunk_id,
                    document_id=row.document_id,
                    content=row.content,
                    similarity=float(row.rank),  # ts_rank를 similarity로 매핑
                    chunk_type=row.chunk_type,
                    page_number=row.page_number,
                    section_title=row.section_title,
                    clause_number=row.clause_number,
                    metadata=row.metadata,
                    document_filename=row.document_filename,
                    document_type=row.document_type,
                    company_name=row.company_name
                )
                search_results.append(search_result)
            
            logger.debug(
                f"키워드 검색 결과: {len(search_results)}개, "
                f"최고 점수={search_results[0].similarity:.4f}" if search_results else "키워드 검색 결과: 0개"
            )
            
            return search_results
        
        except Exception as e:
            logger.error(f"키워드 검색 중 오류 발생: {e}", exc_info=True)
            # 빈 결과 반환 (하이브리드 검색 시 벡터 검색 결과는 활용 가능)
            return []
    
    def reciprocal_rank_fusion(
        self,
        vector_results: List[VectorSearchResult],
        keyword_results: List[VectorSearchResult],
        k: int = None
    ) -> List[Tuple[int, float]]:
        """
        Reciprocal Rank Fusion (RRF) 알고리즘으로 검색 결과를 융합합니다.
        
        RRF는 여러 검색 결과를 융합하는 효과적인 알고리즘으로,
        각 결과의 순위를 기반으로 점수를 계산합니다.
        
        공식: score = sum(1 / (k + rank + 1))
        
        Args:
            vector_results: 벡터 검색 결과 리스트
            keyword_results: 키워드 검색 결과 리스트
            k: RRF 파라미터 (기본: 60, 낮은 순위에 대한 페널티 조정)
        
        Returns:
            (chunk_id, rrf_score) 튜플 리스트 (점수 내림차순 정렬)
        
        References:
            Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009).
            "Reciprocal rank fusion outperforms condorcet and individual rank learning methods"
        """
        if k is None:
            k = self.RRF_K
        
        scores = {}
        
        # 1. 벡터 검색 결과 점수 계산
        for rank, result in enumerate(vector_results):
            chunk_id = result.chunk_id
            # RRF 공식: 1 / (k + rank + 1)
            score = 1.0 / (k + rank + 1)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + score
        
        # 2. 키워드 검색 결과 점수 계산
        for rank, result in enumerate(keyword_results):
            chunk_id = result.chunk_id
            score = 1.0 / (k + rank + 1)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + score
        
        # 3. 점수 기준으로 내림차순 정렬
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        logger.info(
            f"RRF 융합 완료: "
            f"벡터={len(vector_results)}, "
            f"키워드={len(keyword_results)}, "
            f"융합={len(sorted_results)}, "
            f"k={k}"
        )
        
        return sorted_results
    
    def optimize_context(
        self,
        search_results: List[VectorSearchResult],
        max_tokens: int = None
    ) -> Tuple[List[VectorSearchResult], int]:
        """
        컨텍스트를 최적화하여 토큰 제한을 적용합니다.
        
        LLM의 컨텍스트 윈도우 제한을 고려하여 검색 결과를 필터링합니다.
        DB의 token_count를 우선 사용하고, 없으면 동적으로 계산합니다.
        
        Args:
            search_results: 검색 결과 리스트
            max_tokens: 최대 토큰 수 (기본: 8000)
        
        Returns:
            (최적화된 결과 리스트, 총 토큰 수) 튜플
        """
        if max_tokens is None:
            max_tokens = self.MAX_CONTEXT_TOKENS
        
        optimized_results = []
        total_tokens = 0
        
        for result in search_results:
            # 1. 토큰 수 결정 (DB의 token_count 우선 사용)
            # VectorSearchResult에는 token_count가 없으므로 동적 계산
            # (추후 VectorSearchResult에 token_count 추가 고려)
            tokens = len(self.encoding.encode(result.content))
            
            # 2. 토큰 제한 확인
            if total_tokens + tokens <= max_tokens:
                optimized_results.append(result)
                total_tokens += tokens
            else:
                # 토큰 제한 초과 시 중단
                logger.info(
                    f"토큰 제한 도달: {total_tokens}/{max_tokens} "
                    f"(다음 청크: {tokens}토큰)"
                )
                break
        
        logger.info(
            f"컨텍스트 최적화 완료: "
            f"{len(optimized_results)}/{len(search_results)}개 청크, "
            f"{total_tokens}토큰 (제한: {max_tokens})"
        )
        
        return optimized_results, total_tokens
    
    async def hybrid_search(
        self,
        session: AsyncSession,
        query: str,
        limit: int = 10,
        max_tokens: int = None,
        threshold: float = 0.7,
        document_type: Optional[str] = None,
        clause_number: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Tuple[List[VectorSearchResult], int]:
        """
        하이브리드 검색 (벡터 + 키워드)
        
        벡터 검색과 키워드 검색을 병렬로 실행하고,
        RRF 알고리즘으로 융합한 후 컨텍스트 최적화를 적용합니다.
        
        Args:
            session: 데이터베이스 세션
            query: 검색 쿼리
            limit: 최대 결과 수 (기본: 10)
            max_tokens: 최대 토큰 수 (기본: 8000)
            threshold: 벡터 검색 유사도 임계값 (기본: 0.7)
            document_type: 문서 타입 필터 (선택사항)
            clause_number: 조항 번호 필터 (선택사항)
            user_id: 사용자 ID (로그 기록용)
        
        Returns:
            (검색 결과 리스트, 총 토큰 수) 튜플
        """
        start_time = time.time()
        
        logger.info(
            f"하이브리드 검색 시작: query='{query[:50]}...', "
            f"limit={limit}, threshold={threshold}"
        )
        
        # 1. 벡터 검색과 키워드 검색 순차 실행
        # SQLAlchemy 비동기 세션은 동시 쿼리를 지원하지 않으므로 순차 실행
        logger.debug("벡터 검색 실행 중...")
        try:
            vector_results = await self.vector_search_service.search(
                session=session,
                query=query,
                threshold=threshold,
                limit=limit * 2,  # RRF 융합을 위해 더 많이 가져옴
                document_type=document_type,
                clause_number=clause_number,
                user_id=user_id
            )
        except Exception as e:
            logger.error(f"벡터 검색 실패: {e}")
            vector_results = []
        
        logger.debug("키워드 검색 실행 중...")
        try:
            keyword_results = await self.keyword_search(
                session=session,
                query=query,
                limit=limit * 2,  # RRF 융합을 위해 더 많이 가져옴
                document_type=document_type,
                clause_number=clause_number
            )
        except Exception as e:
            logger.error(f"키워드 검색 실패: {e}")
            keyword_results = []
        
        logger.info(
            f"순차 검색 완료: 벡터={len(vector_results)}개, "
            f"키워드={len(keyword_results)}개"
        )
        
        # 검색 결과가 모두 없는 경우
        if not vector_results and not keyword_results:
            logger.warning("벡터 및 키워드 검색 결과 모두 없음")
            return [], 0
        
        # 3. RRF 융합
        fused_chunk_ids = self.reciprocal_rank_fusion(
            vector_results=vector_results,
            keyword_results=keyword_results
        )
        
        # 4. chunk_id 캐싱 및 결과 매핑
        # 재조회 없이 기존 결과 재사용
        chunk_cache = {}
        for result in vector_results + keyword_results:
            if result.chunk_id not in chunk_cache:
                chunk_cache[result.chunk_id] = result
        
        merged_results = []
        for chunk_id, rrf_score in fused_chunk_ids[:limit]:
            if chunk_id in chunk_cache:
                result = chunk_cache[chunk_id]
                # RRF 점수를 similarity로 저장 (통일된 인터페이스)
                result.similarity = rrf_score
                merged_results.append(result)
        
        logger.info(
            f"RRF 융합 완료: {len(fused_chunk_ids)}개 중 {len(merged_results)}개 선택"
        )
        
        # 5. 컨텍스트 최적화 (토큰 제한)
        optimized_results, total_tokens = self.optimize_context(
            search_results=merged_results,
            max_tokens=max_tokens
        )
        
        # 6. 검색 로그 기록
        response_time_ms = int((time.time() - start_time) * 1000)
        
        await self.vector_search_service._log_search(
            session=session,
            query=query,
            search_type="hybrid",
            results_count=len(optimized_results),
            top_similarity=optimized_results[0].similarity if optimized_results else 0.0,
            response_time_ms=response_time_ms,
            user_id=user_id
        )
        
        logger.info(
            f"하이브리드 검색 완료: {len(optimized_results)}개 결과, "
            f"{total_tokens}토큰, 응답시간={response_time_ms}ms"
        )
        
        return optimized_results, total_tokens

