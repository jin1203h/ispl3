"""
텍스트 청킹 서비스
Markdown 텍스트를 의미 있는 청크로 분할합니다.
"""
import re
import hashlib
from typing import List, Dict, Any
from dataclasses import dataclass
import logging
import tiktoken

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """청크 데이터 클래스"""
    content: str
    chunk_index: int
    chunk_type: str  # 'text', 'table', 'image'
    page_number: int = None  # Vision의 물리적 순서 (나중에 할당)
    pdf_page_number: int = None  # PDF 내부 인쇄 페이지 번호 (Markdown에서 추출)
    section_title: str = None
    clause_number: str = None
    token_count: int = 0
    content_hash: str = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """해시 및 메타데이터 자동 생성"""
        if not self.content_hash:
            self.content_hash = self._generate_hash()
        if self.metadata is None:
            self.metadata = {}
    
    def _generate_hash(self) -> str:
        """SHA-256 해시 생성"""
        return hashlib.sha256(self.content.encode('utf-8')).hexdigest()


class TextChunker:
    """텍스트 청킹 서비스"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        overlap: int = 100,
        encoding_name: str = "cl100k_base"
    ):
        """
        초기화
        
        Args:
            chunk_size: 청크 크기 (토큰 수)
            overlap: 청크 간 중복 (토큰 수)
            encoding_name: OpenAI 인코딩 이름
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoding = tiktoken.get_encoding(encoding_name)
        logger.info(
            f"TextChunker 초기화: chunk_size={chunk_size}, "
            f"overlap={overlap}, encoding={encoding_name}"
        )
    
    def count_tokens(self, text: str) -> int:
        """
        텍스트의 토큰 수를 계산합니다.
        
        Args:
            text: 입력 텍스트
        
        Returns:
            토큰 수
        """
        return len(self.encoding.encode(text))
    
    def chunk_text(
        self,
        text: str,
        document_id: int = None,
        page_number: int = None
    ) -> List[Chunk]:
        """
        텍스트를 고정 크기 청크로 분할합니다.
        
        Args:
            text: 입력 텍스트
            document_id: 문서 ID
            page_number: 페이지 번호
        
        Returns:
            Chunk 리스트
        """
        if not text or len(text.strip()) == 0:
            logger.warning("빈 텍스트가 입력되었습니다.")
            return []
        
        # 토큰화
        tokens = self.encoding.encode(text)
        total_tokens = len(tokens)
        logger.info(f"텍스트 청킹 시작: {total_tokens}토큰")
        
        chunks = []
        chunk_index = 0
        start = 0
        
        while start < total_tokens:
            # 청크 범위 계산
            end = min(start + self.chunk_size, total_tokens)
            chunk_tokens = tokens[start:end]
            
            # 토큰을 텍스트로 디코딩 (에러 처리 강화)
            try:
                chunk_text = self.encoding.decode(chunk_tokens)
                
                # Replacement character 확인 및 제거
                if '\ufffd' in chunk_text or '�' in chunk_text:
                    logger.warning(
                        f"청크 {chunk_index}에 replacement character 감지. "
                        f"텍스트 정리 중..."
                    )
                    # Replacement character 제거
                    chunk_text = chunk_text.replace('\ufffd', '')
                    chunk_text = chunk_text.replace('�', '')
                    
            except Exception as e:
                logger.error(f"토큰 디코딩 실패 (청크 {chunk_index}): {e}")
                # 대체 방법: 원본 텍스트에서 직접 추출
                char_start = len(self.encoding.decode(tokens[:start]))
                char_end = len(self.encoding.decode(tokens[:end]))
                chunk_text = text[char_start:char_end]
            
            # 빈 청크 건너뛰기
            if not chunk_text.strip():
                start = end - self.overlap
                continue
            
            # Chunk 객체 생성
            chunk = Chunk(
                content=chunk_text,
                chunk_index=chunk_index,
                chunk_type="text",
                page_number=page_number,
                token_count=len(chunk_tokens),
                metadata={
                    "start_token": start,
                    "end_token": end,
                    "document_id": document_id
                }
            )
            chunks.append(chunk)
            
            # 다음 청크 시작 위치 (오버랩 적용)
            start = end - self.overlap
            chunk_index += 1
            
            # 무한 루프 방지
            if start >= total_tokens - self.overlap:
                break
        
        logger.info(f"청킹 완료: {len(chunks)}개 청크 생성")
        return chunks
    
    def chunk_markdown(
        self,
        markdown_text: str,
        document_id: int = None,
        extract_metadata: bool = True
    ) -> List[Chunk]:
        """
        Markdown 텍스트를 청킹하고 메타데이터를 추출합니다.
        표 분리 없이 전체를 text 청킹합니다.
        
        Args:
            markdown_text: Markdown 텍스트
            document_id: 문서 ID
            extract_metadata: 메타데이터 추출 여부
        
        Returns:
            Chunk 리스트
        """
        # 표 분리 없이 전체를 text 청킹
        chunks = self.chunk_text(markdown_text, document_id)
        
        # 메타데이터 추출 (선택적)
        if extract_metadata:
            chunks = self._extract_chunk_metadata(chunks, markdown_text)
        
        logger.info(f"Markdown 청킹 완료: 총 {len(chunks)}개 (표 분리 없음)")
        
        return chunks
    
    def _extract_tables(self, markdown_text: str) -> List[Dict[str, Any]]:
        """
        Markdown 텍스트에서 표를 추출합니다.
        
        Args:
            markdown_text: Markdown 텍스트
        
        Returns:
            표 리스트
        """
        tables = []
        # Markdown 표 패턴 (| ... | 형식)
        pattern = r'(\|[^\n]+\|\n(?:\|[-:\s]+\|+\n)?(?:\|[^\n]+\|\n)*)'
        
        matches = re.finditer(pattern, markdown_text)
        for i, match in enumerate(matches):
            tables.append({
                "index": i,
                "content": match.group(0).strip(),
                "start": match.start(),
                "end": match.end()
            })
        
        logger.info(f"표 추출: {len(tables)}개")
        return tables
    
    def _extract_chunk_metadata(
        self,
        chunks: List[Chunk],
        markdown_text: str
    ) -> List[Chunk]:
        """
        청크에서 메타데이터를 추출합니다.
        
        Args:
            chunks: Chunk 리스트
            markdown_text: 원본 Markdown
        
        Returns:
            메타데이터가 추가된 Chunk 리스트
        """
        # 섹션 제목 추출 (# 헤더)
        section_headers = self._extract_section_headers(markdown_text)
        
        # 조항 번호 추출 (제N조, 제N장 등)
        clause_pattern = r'제\s*\d+\s*[조장절항]'
        
        for chunk in chunks:
            content = chunk.content
            
            # 섹션 제목 찾기 (가장 가까운 이전 헤더)
            chunk.section_title = self._find_nearest_section(
                content,
                markdown_text,
                section_headers
            )
            
            # 조항 번호 찾기
            clause_match = re.search(clause_pattern, content)
            if clause_match:
                chunk.clause_number = clause_match.group(0).strip()
            
            # 페이지 번호 추정 (### 숫자 패턴)
            page_match = re.search(r'^###\s+(\d+)\s+', content, re.MULTILINE)
            
            if page_match:
                chunk.pdf_page_number = int(page_match.group(1))
        
        return chunks
    
    def _extract_section_headers(self, markdown_text: str) -> List[Dict]:
        """
        Markdown에서 섹션 헤더를 추출합니다.
        
        Args:
            markdown_text: Markdown 텍스트
        
        Returns:
            헤더 리스트
        """
        headers = []
        pattern = r'^(#{1,6})\s+(.+)$'
        
        for match in re.finditer(pattern, markdown_text, re.MULTILINE):
            level = len(match.group(1))
            title = match.group(2).strip()
            position = match.start()
            headers.append({
                "level": level,
                "title": title,
                "position": position
            })
        
        return headers
    
    def _find_nearest_section(
        self,
        chunk_content: str,
        full_text: str,
        headers: List[Dict]
    ) -> str:
        """
        청크에 가장 가까운 섹션 제목을 찾습니다.
        
        Args:
            chunk_content: 청크 내용
            full_text: 전체 텍스트
            headers: 헤더 리스트
        
        Returns:
            섹션 제목
        """
        if not headers:
            return None
        
        # 청크의 시작 위치 찾기 (근사값)
        chunk_start = full_text.find(chunk_content[:50]) if len(chunk_content) >= 50 else 0
        
        # 가장 가까운 이전 헤더 찾기
        nearest_header = None
        for header in headers:
            if header['position'] <= chunk_start:
                if nearest_header is None or header['position'] > nearest_header['position']:
                    nearest_header = header
        
        return nearest_header['title'] if nearest_header else None

