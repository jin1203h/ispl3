"""
청크 확장 서비스
인접 청크를 가져와 컨텍스트를 확장하는 기능을 제공합니다.
"""
import logging
import re
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import tiktoken

from services.vector_search import VectorSearchResult

logger = logging.getLogger(__name__)


class ChunkExpansionService:
    """
    청크 확장 서비스
    
    청크의 내용이 잘렸거나 불완전한 경우,
    인접한 청크를 가져와 컨텍스트를 확장합니다.
    """
    
    # 토큰 제한 (GPT-4o 기준 - 128K 컨텍스트)
    # GPT-4o: 128,000 토큰
    # - 시스템 프롬프트: ~800 토큰
    # - 질문: ~200 토큰
    # - 답변 생성 공간: ~1000 토큰
    # - 안전 마진: ~3000 토큰
    # ────────────────────────────
    # 컨텍스트 허용: ~15000 토큰
    MAX_CONTEXT_TOKENS = 15000  # gpt-4o 변경으로 6000 → 15000 증가
    
    def __init__(self):
        """청크 확장 서비스 초기화"""
        # GPT-4 호환 인코딩
        self.encoding = tiktoken.get_encoding("cl100k_base")
        logger.info(
            f"ChunkExpansionService 초기화 완료: "
            f"MAX_CONTEXT_TOKENS={self.MAX_CONTEXT_TOKENS}"
        )
    
    async def get_adjacent_chunks(
        self,
        session: AsyncSession,
        chunk_id: int,
        direction: str = "both",
        limit: int = 1
    ) -> Dict[str, List[VectorSearchResult]]:
        """
        현재 청크의 인접 청크를 가져옵니다.
        
        Args:
            session: 데이터베이스 세션
            chunk_id: 기준 청크 ID
            direction: 방향 ("prev", "next", "both")
            limit: 각 방향에서 가져올 청크 수
        
        Returns:
            {
                "prev": [이전 청크들],
                "next": [다음 청크들]
            }
        """
        try:
            # 기준 청크 정보 조회
            base_query = text("""
                SELECT document_id, chunk_index
                FROM document_chunks
                WHERE id = :chunk_id
            """)
            
            result = await session.execute(base_query, {"chunk_id": chunk_id})
            base_row = result.fetchone()
            
            if not base_row:
                logger.warning(f"청크 {chunk_id}를 찾을 수 없습니다.")
                return {"prev": [], "next": []}
            
            document_id = base_row.document_id
            chunk_index = base_row.chunk_index
            
            adjacent_chunks = {"prev": [], "next": []}
            
            # 이전 청크 가져오기
            if direction in ["prev", "both"]:
                prev_query = text("""
                    SELECT 
                        c.id as chunk_id,
                        c.document_id,
                        c.content,
                        c.chunk_type,
                        c.page_number,
                        c.section_title,
                        c.clause_number,
                        c.metadata,
                        c.chunk_index,
                        d.filename as document_filename,
                        d.document_type,
                        d.company_name
                    FROM document_chunks c
                    INNER JOIN documents d ON c.document_id = d.id
                    WHERE c.document_id = :document_id
                        AND c.chunk_index < :chunk_index
                        AND d.status = 'active'
                    ORDER BY c.chunk_index DESC
                    LIMIT :limit
                """)
                
                result = await session.execute(
                    prev_query,
                    {
                        "document_id": document_id,
                        "chunk_index": chunk_index,
                        "limit": limit
                    }
                )
                prev_rows = result.fetchall()
                
                # 순서를 원래대로 되돌림 (오래된 것부터)
                for row in reversed(prev_rows):
                    adjacent_chunks["prev"].append(self._row_to_result(row))
            
            # 다음 청크 가져오기
            if direction in ["next", "both"]:
                next_query = text("""
                    SELECT 
                        c.id as chunk_id,
                        c.document_id,
                        c.content,
                        c.chunk_type,
                        c.page_number,
                        c.section_title,
                        c.clause_number,
                        c.metadata,
                        c.chunk_index,
                        d.filename as document_filename,
                        d.document_type,
                        d.company_name
                    FROM document_chunks c
                    INNER JOIN documents d ON c.document_id = d.id
                    WHERE c.document_id = :document_id
                        AND c.chunk_index > :chunk_index
                        AND d.status = 'active'
                    ORDER BY c.chunk_index ASC
                    LIMIT :limit
                """)
                
                result = await session.execute(
                    next_query,
                    {
                        "document_id": document_id,
                        "chunk_index": chunk_index,
                        "limit": limit
                    }
                )
                next_rows = result.fetchall()
                
                for row in next_rows:
                    adjacent_chunks["next"].append(self._row_to_result(row))
            
            logger.info(
                f"인접 청크 조회 완료: chunk_id={chunk_id}, "
                f"prev={len(adjacent_chunks['prev'])}, "
                f"next={len(adjacent_chunks['next'])}"
            )
            
            return adjacent_chunks
        
        except Exception as e:
            logger.error(f"인접 청크 조회 중 오류 발생: {e}", exc_info=True)
            return {"prev": [], "next": []}
    
    def _row_to_result(self, row) -> VectorSearchResult:
        """데이터베이스 행을 VectorSearchResult로 변환"""
        return VectorSearchResult(
            chunk_id=row.chunk_id,
            document_id=row.document_id,
            content=row.content,
            similarity=1.0,  # 인접 청크는 유사도를 1.0으로 설정
            chunk_type=row.chunk_type,
            page_number=row.page_number,
            section_title=row.section_title,
            clause_number=row.clause_number,
            metadata=row.metadata or {},
            document_filename=row.document_filename,
            document_type=row.document_type,
            company_name=row.company_name
        )
    
    def _check_new_section_start(self, content: str, primary_content: str = None) -> bool:
        """
        청크 내용이 새로운 섹션(조항, 장, 절, 표 등)으로 시작하는지 체크
        
        Args:
            content: 체크할 청크 내용
            primary_content: 메인 청크 내용 (표 계속 여부 판단용)
        
        Returns:
            True: 새 섹션 시작, False: 기존 섹션 계속
        """
        if not content or not content.strip():
            return False
        
        # 첫 줄 추출
        lines = content.strip().split('\n')
        first_line = lines[0].strip() if lines else ""
        
        # 표로 시작하는 경우 특별 처리
        if first_line.startswith('|'):
            # 메인 청크에도 표가 있으면 → 표 계속 (새 섹션 아님)
            if primary_content and '|' in primary_content:
                logger.debug("표 계속 감지 → 새 섹션 아님")
                return False
            # 메인 청크에 표가 없으면 → 새 표 시작 (새 섹션)
            else:
                logger.debug(f"새 표 시작 감지: '{first_line[:50]}...'")
                return True
        
        # 상위 레벨 섹션 시작 패턴들
        patterns = [
            r'^제\d+조',           # 제XX조
            r'^제\d+장',           # 제XX장  
            r'^제\d+절',           # 제XX절
            r'^\d+\.\s*[가-힣]+',  # 1. 제목 형식 (예: "1. 보험금 지급")
        ]
        
        for pattern in patterns:
            if re.match(pattern, first_line):
                logger.debug(f"새 섹션 감지: '{first_line[:50]}...'")
                return True
        
        return False
    
    def merge_chunks(
        self,
        primary_chunk: VectorSearchResult,
        prev_chunks: List[VectorSearchResult],
        next_chunks: List[VectorSearchResult],
        max_tokens: int = None
    ) -> Dict[str, Any]:
        """
        메인 청크와 인접 청크를 병합합니다.
        
        Args:
            primary_chunk: 메인 청크
            prev_chunks: 이전 청크들
            next_chunks: 다음 청크들
            max_tokens: 최대 토큰 수
        
        Returns:
            {
                "merged_content": "병합된 내용",
                "included_chunks": [포함된 청크 ID들],
                "total_tokens": 총 토큰 수,
                "truncated": 토큰 제한으로 잘렸는지 여부
            }
        """
        if max_tokens is None:
            max_tokens = self.MAX_CONTEXT_TOKENS
        
        # 청크 내용과 메타데이터 수집
        chunks_data = []
        
        # 이전 청크 추가 (순서대로)
        for chunk in prev_chunks:
            chunks_data.append({
                "chunk_id": chunk.chunk_id,
                "content": chunk.content,
                "position": "prev",
                "tokens": len(self.encoding.encode(chunk.content))
            })
        
        # 메인 청크 추가 (필수)
        primary_tokens = len(self.encoding.encode(primary_chunk.content))
        chunks_data.append({
            "chunk_id": primary_chunk.chunk_id,
            "content": primary_chunk.content,
            "position": "primary",
            "tokens": primary_tokens
        })
        
        # 다음 청크 추가 (순서대로)
        for chunk in next_chunks:
            chunks_data.append({
                "chunk_id": chunk.chunk_id,
                "content": chunk.content,
                "position": "next",
                "tokens": len(self.encoding.encode(chunk.content))
            })
        
        # 토큰 제한 내에서 병합
        included_chunks = []
        merged_parts = []
        total_tokens = 0
        truncated = False
        
        # 메인 청크는 항상 포함
        primary_idx = len(prev_chunks)
        included_chunks.append(chunks_data[primary_idx]["chunk_id"])
        merged_parts.append(chunks_data[primary_idx]["content"])
        total_tokens += chunks_data[primary_idx]["tokens"]
        
        # 토큰 제한 확인
        if total_tokens > max_tokens:
            logger.warning(
                f"메인 청크가 토큰 제한 초과: {total_tokens}/{max_tokens}"
            )
            truncated = True
        
        # 이전/다음 청크 추가 (토큰 제한 내에서)
        # 전략: 이전 청크와 다음 청크를 번갈아가며 추가
        prev_idx = primary_idx - 1
        next_idx = primary_idx + 1
        
        while (prev_idx >= 0 or next_idx < len(chunks_data)) and not truncated:
            # 다음 청크 추가 시도
            if next_idx < len(chunks_data):
                chunk_data = chunks_data[next_idx]
                
                # ⭐ 새 섹션 시작 체크 (병합 중단 조건)
                # primary_chunk의 내용을 전달하여 표 계속 여부 판단
                if self._check_new_section_start(
                    chunk_data["content"], 
                    primary_content=primary_chunk.content
                ):
                    logger.info(
                        f"청크 {chunk_data['chunk_id']}: 새 섹션 시작 감지 → 병합 중단"
                    )
                    break
                
                # 토큰 제한 체크
                if total_tokens + chunk_data["tokens"] <= max_tokens:
                    merged_parts.append(chunk_data["content"])
                    included_chunks.append(chunk_data["chunk_id"])
                    total_tokens += chunk_data["tokens"]
                    next_idx += 1
                else:
                    truncated = True
                    break
            
            # 이전 청크 추가 시도
            if prev_idx >= 0:
                chunk_data = chunks_data[prev_idx]
                
                # ⭐ 메인 청크가 새 섹션 시작이면 이전 청크는 다른 섹션
                # 이전 청크의 끝이 완전한지만 체크 (새 섹션 체크는 불필요)
                
                # 토큰 제한 체크
                if total_tokens + chunk_data["tokens"] <= max_tokens:
                    merged_parts.insert(0, chunk_data["content"])
                    included_chunks.insert(0, chunk_data["chunk_id"])
                    total_tokens += chunk_data["tokens"]
                    prev_idx -= 1
                else:
                    truncated = True
                    break
        
        # 최종 병합
        merged_content = "\n\n".join(merged_parts)
        
        logger.info(
            f"청크 병합 완료: "
            f"included={len(included_chunks)}, "
            f"tokens={total_tokens}/{max_tokens}, "
            f"truncated={truncated}"
        )
        logger.info(
            f"포함된 청크 ID들: {included_chunks}"
        )
        logger.info(
            f"병합된 내용 끝부분(100자): ...{merged_content[-100:]}"
        )
        
        return {
            "merged_content": merged_content,
            "included_chunks": included_chunks,
            "total_tokens": total_tokens,
            "truncated": truncated
        }
    
    async def expand_search_results(
        self,
        session: AsyncSession,
        search_results: List[VectorSearchResult],
        chunks_to_expand: List[Dict[str, Any]],  # ⭐ 딕셔너리 리스트로 변경 (방향 정보 포함)
        max_tokens: int = None
    ) -> List[VectorSearchResult]:
        """
        검색 결과에서 지정된 청크들을 확장합니다.
        
        Args:
            session: 데이터베이스 세션
            search_results: 원본 검색 결과
            chunks_to_expand: 확장 정보 리스트 [{"chunk_id": int, "direction": str}, ...]
            max_tokens: 최대 토큰 수
        
        Returns:
            확장된 검색 결과 목록
        """
        if max_tokens is None:
            max_tokens = self.MAX_CONTEXT_TOKENS
        
        expanded_results = []
        total_tokens = 0
        
        # 확장 정보를 딕셔너리로 변환 (chunk_id → direction)
        expand_map = {}
        for item in chunks_to_expand:
            if isinstance(item, dict):
                expand_map[item["chunk_id"]] = item.get("direction", "both")
            else:
                # 하위 호환성: 정수만 있으면 both로
                expand_map[item] = "both"
        
        for result in search_results:
            if result.chunk_id in expand_map:
                # 확장이 필요한 청크
                direction = expand_map[result.chunk_id]
                logger.info(f"청크 {result.chunk_id} 확장 중 (direction={direction})...")
                
                # 토큰 제한 체크
                if total_tokens >= max_tokens:
                    logger.warning(
                        f"토큰 제한 도달: {total_tokens}/{max_tokens}, "
                        f"청크 {result.chunk_id} 확장 생략"
                    )
                    expanded_results.append(result)
                    continue
                
                # 인접 청크 가져오기 (방향 지정)
                adjacent = await self.get_adjacent_chunks(
                    session=session,
                    chunk_id=result.chunk_id,
                    direction=direction,  # ⭐ 방향 정보 사용
                    limit=2  # 각 방향에서 최대 2개
                )
                
                # 병합 (남은 토큰만 사용)
                merged = self.merge_chunks(
                    primary_chunk=result,
                    prev_chunks=adjacent["prev"],
                    next_chunks=adjacent["next"],
                    max_tokens=max_tokens - total_tokens  # ⭐ 남은 토큰만 사용
                )
                
                # 토큰 제한 초과 확인
                if total_tokens + merged["total_tokens"] > max_tokens:
                    logger.warning(
                        f"토큰 제한 초과: {total_tokens + merged['total_tokens']}/{max_tokens}, "
                        f"청크 {result.chunk_id} 원본 사용"
                    )
                    # 확장 없이 원본 사용
                    chunk_tokens = len(self.encoding.encode(result.content))
                    if total_tokens + chunk_tokens <= max_tokens:
                        expanded_results.append(result)
                        total_tokens += chunk_tokens
                    continue
                
                # 확장된 청크 생성
                expanded_result = VectorSearchResult(
                    chunk_id=result.chunk_id,
                    document_id=result.document_id,
                    content=merged["merged_content"],  # 병합된 내용
                    similarity=result.similarity,
                    chunk_type=result.chunk_type,
                    page_number=result.page_number,
                    section_title=result.section_title,
                    clause_number=result.clause_number,
                    metadata={
                        **result.metadata,
                        "expanded": True,
                        "included_chunks": merged["included_chunks"],
                        "total_tokens": merged["total_tokens"],
                        "truncated": merged["truncated"]
                    },
                    document_filename=result.document_filename,
                    document_type=result.document_type,
                    company_name=result.company_name
                )
                
                expanded_results.append(expanded_result)
                total_tokens += merged["total_tokens"]
            else:
                # 확장이 필요없는 청크는 그대로 유지
                chunk_tokens = len(self.encoding.encode(result.content))
                
                # 토큰 제한 체크
                if total_tokens + chunk_tokens > max_tokens:
                    logger.warning(
                        f"토큰 제한 도달: {total_tokens}/{max_tokens}, "
                        f"청크 {result.chunk_id} 제외"
                    )
                    break
                
                expanded_results.append(result)
                total_tokens += chunk_tokens
        
        logger.info(
            f"검색 결과 확장 완료: {len(expanded_results)}개, "
            f"{total_tokens}/{max_tokens} 토큰"
            # VectorSearchResult 객체에는 model_dump() 메서드가 없습니다.
            # to_dict() 메서드를 사용해야 합니다.
            f"검색 결과 expanded_results content: {[result.content for result in expanded_results]} "
        )
        
        return expanded_results

