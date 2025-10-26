"""
벡터 검색 서비스
pgvector를 사용하여 코사인 유사도 기반 벡터 검색을 수행합니다.
"""
import time
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.embedding_service import EmbeddingService
from models.search_log import SearchLog
from models.document_chunk import DocumentChunk
from models.document import Document

logger = logging.getLogger(__name__)


class VectorSearchResult:
    """벡터 검색 결과를 담는 데이터 클래스"""
    
    def __init__(
        self,
        chunk_id: int,
        document_id: int,
        content: str,
        similarity: float,
        chunk_type: str,
        page_number: Optional[int] = None,
        section_title: Optional[str] = None,
        clause_number: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        document_filename: Optional[str] = None,
        document_type: Optional[str] = None,
        company_name: Optional[str] = None
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.content = content
        self.similarity = similarity
        self.chunk_type = chunk_type
        self.page_number = page_number
        self.section_title = section_title
        self.clause_number = clause_number
        self.metadata = metadata or {}
        self.document_filename = document_filename
        self.document_type = document_type
        self.company_name = company_name
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "content": self.content,
            "similarity": self.similarity,
            "chunk_type": self.chunk_type,
            "page_number": self.page_number,
            "section_title": self.section_title,
            "clause_number": self.clause_number,
            "metadata": self.metadata,
            "document": {
                "filename": self.document_filename,
                "type": self.document_type,
                "company_name": self.company_name
            }
        }


class VectorSearchService:
    """벡터 검색 서비스"""
    
    DEFAULT_THRESHOLD = 0.7  # 유사도 임계값
    DEFAULT_LIMIT = 10  # 기본 검색 결과 수
    
    def __init__(self, embedding_service=None):
        """
        초기화
        
        Args:
            embedding_service: EmbeddingService 인스턴스 (의존성 주입)
        """
        # 의존성 주입: 외부에서 주입되지 않으면 기본 생성 (하위 호환성)
        if embedding_service is None:
            from services.embedding_service import EmbeddingService
            embedding_service = EmbeddingService()
            logger.warning("VectorSearchService: embedding_service가 주입되지 않아 기본 인스턴스 생성")
        
        self.embedding_service = embedding_service
        logger.info(
            f"VectorSearchService 초기화: threshold={self.DEFAULT_THRESHOLD}, "
            f"limit={self.DEFAULT_LIMIT}"
        )
    
    async def search(
        self,
        session: AsyncSession,
        query: str,
        threshold: Optional[float] = None,
        limit: Optional[int] = None,
        document_type: Optional[str] = None,
        clause_number: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> List[VectorSearchResult]:
        """
        벡터 검색을 수행합니다.
        
        Args:
            session: 데이터베이스 세션
            query: 검색 쿼리
            threshold: 유사도 임계값 (기본: 0.7)
            limit: 최대 결과 수 (기본: 10)
            document_type: 문서 타입 필터 (선택사항)
            clause_number: 조항 번호 필터 (예: "제15조")
            user_id: 사용자 ID (로그 기록용)
        
        Returns:
            VectorSearchResult 리스트
        """
        start_time = time.time()
        
        # 기본값 설정
        threshold = threshold or self.DEFAULT_THRESHOLD
        limit = limit or self.DEFAULT_LIMIT
        
        logger.info(
            f"벡터 검색 시작: query='{query[:50]}...', "
            f"threshold={threshold}, limit={limit}"
        )
        
        try:
            # 1. 쿼리 임베딩 생성
            query_embedding = await self.embedding_service.create_embedding(query)
            
            if not self.embedding_service.validate_embedding(query_embedding):
                logger.error("쿼리 임베딩 생성 실패")
                return []
            
            logger.info(f"쿼리 임베딩 생성 완료: dim={len(query_embedding)}")
            
            # 2. pgvector 코사인 유사도 검색
            results = await self._search_vectors(
                session=session,
                query_embedding=query_embedding,
                threshold=threshold,
                limit=limit,
                document_type=document_type,
                clause_number=clause_number
            )
            
            # 3. 검색 로그 기록
            response_time_ms = int((time.time() - start_time) * 1000)
            top_similarity = results[0].similarity if results else 0.0
            
            await self._log_search(
                session=session,
                query=query,
                search_type="vector",
                results_count=len(results),
                top_similarity=top_similarity,
                response_time_ms=response_time_ms,
                user_id=user_id
            )
            
            logger.info(
                f"벡터 검색 완료: {len(results)}개 결과, "
                f"응답 시간={response_time_ms}ms, "
                f"최고 유사도={top_similarity:.3f}"
            )
            
            return results
        
        except Exception as e:
            logger.error(f"벡터 검색 중 오류 발생: {e}", exc_info=True)
            raise
    
    async def _search_vectors(
        self,
        session: AsyncSession,
        query_embedding: List[float],
        threshold: float,
        limit: int,
        document_type: Optional[str] = None,
        clause_number: Optional[str] = None
    ) -> List[VectorSearchResult]:
        """
        pgvector를 사용한 코사인 유사도 검색
        
        Args:
            session: 데이터베이스 세션
            query_embedding: 쿼리 임베딩 벡터
            threshold: 유사도 임계값
            limit: 최대 결과 수
            document_type: 문서 타입 필터
            clause_number: 조항 번호 필터 (예: "제15조")
        
        Returns:
            VectorSearchResult 리스트
        """
        # 문서 타입 필터 조건
        document_filter = ""
        if document_type:
            document_filter = "AND d.document_type = :document_type"
        
        # 조항 번호 필터 조건
        clause_filter = ""
        if clause_number:
            clause_filter = "AND c.clause_number = :clause_number"
            logger.info(f"조항 번호 필터 적용: {clause_number}")
        
        # pgvector 코사인 유사도 검색 쿼리
        # <=> 연산자: 코사인 거리 (0: 동일, 2: 완전 반대)
        # 코사인 유사도 = 1 - 코사인 거리
        # pgvector.asyncpg.register_vector()로 타입이 등록되어 있으면
        # Python 리스트를 직접 전달 가능
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
                d.filename as document_filename,
                d.document_type,
                d.company_name,
                1 - (c.embedding <=> :query_embedding) as similarity
            FROM document_chunks c
            INNER JOIN documents d ON c.document_id = d.id
            WHERE 1 - (c.embedding <=> :query_embedding) > :threshold
                AND d.status = 'active'
                {document_filter}
                {clause_filter}
            ORDER BY c.embedding <=> :query_embedding
            LIMIT :limit
        """)
        
        # 파라미터 바인딩
        # Python 리스트를 직접 전달 (register_vector로 타입 등록됨)
        params = {
            "query_embedding": query_embedding,
            "threshold": threshold,
            "limit": limit
        }
        
        if document_type:
            params["document_type"] = document_type
        
        if clause_number:
            params["clause_number"] = clause_number
        
        # 쿼리 실행
        result = await session.execute(query_sql, params)
        rows = result.fetchall()
        
        logger.info(f"pgvector 검색 완료: {len(rows)}개 결과")
        
        # VectorSearchResult 객체로 변환
        search_results = []
        for row in rows:
            search_result = VectorSearchResult(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                content=row.content,
                similarity=float(row.similarity),
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
        
        return search_results
    
    async def _log_search(
        self,
        session: AsyncSession,
        query: str,
        search_type: str,
        results_count: int,
        top_similarity: float,
        response_time_ms: int,
        user_id: Optional[int] = None
    ) -> None:
        """
        검색 로그를 기록합니다.
        
        Args:
            session: 데이터베이스 세션
            query: 검색 쿼리
            search_type: 검색 타입 ('vector', 'keyword', 'hybrid')
            results_count: 결과 수
            top_similarity: 최고 유사도 점수
            response_time_ms: 응답 시간 (밀리초)
            user_id: 사용자 ID (선택사항)
        """
        try:
            search_log = SearchLog(
                user_id=user_id,
                query=query,
                search_type=search_type,
                results_count=results_count,
                top_similarity_score=top_similarity,
                response_time_ms=response_time_ms
            )
            session.add(search_log)
            await session.commit()
            
            logger.debug(f"검색 로그 기록 완료: id={search_log.id}")
        
        except Exception as e:
            logger.error(f"검색 로그 기록 실패: {e}")
            # 로그 기록 실패는 치명적이지 않으므로 예외를 전파하지 않음
            await session.rollback()
    
    async def get_similar_chunks(
        self,
        session: AsyncSession,
        chunk_id: int,
        limit: int = 5
    ) -> List[VectorSearchResult]:
        """
        특정 청크와 유사한 청크를 찾습니다.
        
        Args:
            session: 데이터베이스 세션
            chunk_id: 기준 청크 ID
            limit: 최대 결과 수
        
        Returns:
            VectorSearchResult 리스트
        """
        try:
            # 기준 청크 조회
            result = await session.execute(
                text("SELECT embedding FROM document_chunks WHERE id = :chunk_id"),
                {"chunk_id": chunk_id}
            )
            row = result.fetchone()
            
            if not row or row.embedding is None:
                logger.warning(f"청크 {chunk_id}를 찾을 수 없습니다.")
                return []
            
            # 유사한 청크 검색 (자기 자신 제외)
            query_sql = text("""
                SELECT 
                    c.id as chunk_id,
                    c.document_id,
                    c.content,
                    c.chunk_type,
                    c.page_number,
                    c.section_title,
                    c.clause_number,
                    c.metadata,
                    d.filename as document_filename,
                    d.document_type,
                    d.company_name,
                    1 - (c.embedding <=> :reference_embedding) as similarity
                FROM document_chunks c
                INNER JOIN documents d ON c.document_id = d.id
                WHERE c.id != :chunk_id
                    AND d.status = 'active'
                ORDER BY c.embedding <=> :reference_embedding
                LIMIT :limit
            """)
            
            # pgvector 타입을 Python 리스트로 변환
            # register_vector() 후에는 리스트를 직접 전달 가능
            if hasattr(row.embedding, 'tolist'):
                embedding_list = row.embedding.tolist()
            else:
                embedding_list = list(row.embedding)
            
            result = await session.execute(
                query_sql,
                {
                    "reference_embedding": embedding_list,
                    "chunk_id": chunk_id,
                    "limit": limit
                }
            )
            rows = result.fetchall()
            
            # VectorSearchResult 객체로 변환
            search_results = []
            for row in rows:
                search_result = VectorSearchResult(
                    chunk_id=row.chunk_id,
                    document_id=row.document_id,
                    content=row.content,
                    similarity=float(row.similarity),
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
            
            logger.info(f"유사 청크 검색 완료: {len(search_results)}개")
            return search_results
        
        except Exception as e:
            logger.error(f"유사 청크 검색 중 오류: {e}")
            raise

