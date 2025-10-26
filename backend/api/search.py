"""
검색 API 엔드포인트
벡터 검색 및 하이브리드 검색 기능을 제공합니다.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.vector_search import VectorSearchResult
from services.service_container import get_vector_search_service, get_hybrid_search_service

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchRequest(BaseModel):
    """검색 요청 모델"""
    query: str = Field(..., min_length=1, description="검색 쿼리")
    threshold: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=1.0, 
        description="유사도 임계값 (0.0-1.0)"
    )
    limit: Optional[int] = Field(None, ge=1, le=100, description="최대 결과 수")
    document_type: Optional[str] = Field(None, description="문서 타입 필터")
    user_id: Optional[int] = Field(None, description="사용자 ID")


class SearchResultItem(BaseModel):
    """검색 결과 항목"""
    chunk_id: int
    document_id: int
    content: str
    similarity: float
    chunk_type: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    clause_number: Optional[str] = None
    metadata: dict = {}
    document: dict = {}


class SearchResponse(BaseModel):
    """검색 응답 모델"""
    query: str
    results: List[SearchResultItem]
    count: int
    threshold: float
    limit: int


@router.post("/vector", response_model=SearchResponse)
async def vector_search(
    request: SearchRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    벡터 검색을 수행합니다.
    
    - **query**: 검색할 텍스트 (필수)
    - **threshold**: 유사도 임계값 (0.0-1.0, 기본: 0.7)
    - **limit**: 최대 결과 수 (1-100, 기본: 10)
    - **document_type**: 문서 타입 필터 (선택사항)
    - **user_id**: 사용자 ID (로그 기록용, 선택사항)
    
    Returns:
        검색 결과 리스트
    """
    try:
        # 싱글톤 서비스 인스턴스 가져오기
        vector_search_service = get_vector_search_service()
        
        # 벡터 검색 수행
        results = await vector_search_service.search(
            session=session,
            query=request.query,
            threshold=request.threshold,
            limit=request.limit,
            document_type=request.document_type,
            user_id=request.user_id
        )
        
        # 응답 생성
        result_items = [
            SearchResultItem(**result.to_dict())
            for result in results
        ]
        
        response = SearchResponse(
            query=request.query,
            results=result_items,
            count=len(results),
            threshold=request.threshold or vector_search_service.DEFAULT_THRESHOLD,
            limit=request.limit or vector_search_service.DEFAULT_LIMIT
        )
        
        return response
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"검색 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/similar/{chunk_id}", response_model=List[SearchResultItem])
async def get_similar_chunks(
    chunk_id: int,
    limit: int = Query(5, ge=1, le=20, description="최대 결과 수"),
    session: AsyncSession = Depends(get_db)
):
    """
    특정 청크와 유사한 청크를 찾습니다.
    
    - **chunk_id**: 기준 청크 ID
    - **limit**: 최대 결과 수 (기본: 5)
    
    Returns:
        유사한 청크 리스트
    """
    try:
        # 싱글톤 서비스 인스턴스 가져오기
        vector_search_service = get_vector_search_service()
        
        results = await vector_search_service.get_similar_chunks(
            session=session,
            chunk_id=chunk_id,
            limit=limit
        )
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"청크 ID {chunk_id}를 찾을 수 없습니다."
            )
        
        result_items = [
            SearchResultItem(**result.to_dict())
            for result in results
        ]
        
        return result_items
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"유사 청크 검색 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/hybrid", response_model=SearchResponse)
async def hybrid_search(
    request: SearchRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    하이브리드 검색을 수행합니다 (벡터 + 키워드).
    
    벡터 검색(의미 기반)과 키워드 검색(정확한 매칭)을 결합하여
    더 높은 검색 정확도를 제공합니다.
    
    - **query**: 검색할 텍스트 (필수)
    - **threshold**: 유사도 임계값 (0.0-1.0, 기본: 0.5) - 벡터 검색용
    - **limit**: 최대 결과 수 (1-100, 기본: 10)
    - **document_type**: 문서 타입 필터 (선택사항)
    - **user_id**: 사용자 ID (로그 기록용, 선택사항)
    
    Returns:
        검색 결과 리스트 (RRF 알고리즘으로 융합됨)
    """
    try:
        # 싱글톤 서비스 인스턴스 가져오기
        hybrid_search_service = get_hybrid_search_service()
        
        # 하이브리드 검색 수행
        # threshold 기본값을 0.5로 낮춤 (하이브리드에서는 낮은 임계값 사용)
        threshold = request.threshold if request.threshold is not None else 0.5
        
        results, total_tokens = await hybrid_search_service.hybrid_search(
            session=session,
            query=request.query,
            threshold=threshold,
            limit=request.limit,
            document_type=request.document_type,
            user_id=request.user_id
        )
        
        # 응답 생성
        result_items = [
            SearchResultItem(**result.to_dict())
            for result in results
        ]
        
        response = SearchResponse(
            query=request.query,
            results=result_items,
            count=len(result_items),
            threshold=threshold,
            limit=request.limit or 10
        )
        
        return response
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"하이브리드 검색 중 오류가 발생했습니다: {str(e)}"
        )

