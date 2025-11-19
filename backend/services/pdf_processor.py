"""
PDF 전처리 서비스
Path 1(PyMuPDF4LLM) + Path 2(GPT-4 Vision) 통합

처리 방식:
- pymupdf: PyMuPDF4LLM으로 빠른 텍스트 추출
- vision: GPT-4 Vision으로 이미지 기반 추출
- both: 하이브리드 방식 - PyMuPDF 텍스트를 Vision API의 컨텍스트로 활용
  * PyMuPDF로 텍스트 추출 (빠르고 정확)
  * Vision API에 텍스트 + 이미지를 함께 제공
  * Vision이 텍스트를 검증하고 표/이미지/레이아웃 정보를 보완
"""
from pathlib import Path
from typing import Dict, Optional, Literal, List
import logging
from datetime import datetime
import asyncio

from services.pymupdf_extractor import PyMuPDFExtractor
from services.vision_extractor import VisionExtractor
from services.hybrid_merger import HybridMerger
from services.chunker import TextChunker
from services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF 처리 메인 서비스"""
    
    def __init__(self, embedding_service=None, text_chunker=None):
        """
        초기화
        
        Args:
            embedding_service: EmbeddingService 인스턴스 (의존성 주입)
            text_chunker: TextChunker 인스턴스 (의존성 주입)
        """
        self.pymupdf_extractor = PyMuPDFExtractor()
        self.vision_extractor = VisionExtractor()
        self.hybrid_merger = HybridMerger()
        
        # 의존성 주입: 외부에서 주입되지 않으면 기본 생성 (하위 호환성)
        if text_chunker is None:
            from services.chunker import TextChunker
            text_chunker = TextChunker(chunk_size=1000, overlap=100)
            logger.warning("PDFProcessor: text_chunker가 주입되지 않아 기본 인스턴스 생성")
        
        if embedding_service is None:
            from services.embedding_service import EmbeddingService
            embedding_service = EmbeddingService()
            logger.warning("PDFProcessor: embedding_service가 주입되지 않아 기본 인스턴스 생성")
        
        self.chunker = text_chunker
        self.embedding_service = embedding_service
        logger.info("PDFProcessor 초기화 완료")
    
    async def process_pdf(
        self,
        pdf_path: str,
        document_id: int,
        save_markdown: bool = True,
        method: Literal["pymupdf", "vision", "both"] = "pymupdf",
        enable_chunking: bool = False,
        db_session = None  # AsyncSession (optional)
    ) -> Dict:
        """
        PDF 파일 처리
        
        Args:
            pdf_path: PDF 파일 경로
            document_id: 문서 ID
            save_markdown: Markdown 파일 저장 여부
            method: 처리 방법 ("pymupdf", "vision", "both")
            enable_chunking: 청킹 및 임베딩 활성화 여부
            
        Returns:
            처리 결과
        """
        start_time = datetime.now()
        logger.info(
            f"PDF 처리 시작: {pdf_path} "
            f"(document_id={document_id}, method={method})"
        )
        
        try:
            if method == "pymupdf":
                result = self._process_with_pymupdf(pdf_path, document_id)
            elif method == "vision":
                result = await self._process_with_vision_async(pdf_path, document_id)
            elif method == "both":
                result = await self._process_with_both_async(pdf_path, document_id)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            # Markdown 파일 저장
            if save_markdown:
                markdown_path = self._save_markdown(
                    result['markdown'],
                    pdf_path,
                    document_id,
                    method
                )
                result['markdown_path'] = str(markdown_path)
            
            # 청킹 및 임베딩
            if enable_chunking:
                logger.info(f"청킹 시작: enable_chunking={enable_chunking}, session={'있음' if db_session else '없음'}")
                pages_info = result.get('pages', [])  # Vision의 pages 정보
                chunks_data = await self._chunk_and_embed(
                    result['markdown'],
                    document_id,
                    db_session,
                    pages_info=pages_info
                )
                result['chunks'] = chunks_data
                logger.info(f"청킹 완료: {chunks_data.get('total_chunks', 0)}개 청크")
            else:
                logger.warning("청킹이 비활성화되어 있습니다!")
            
            # 처리 시간 계산
            processing_time = (datetime.now() - start_time).total_seconds()
            result['processing_time_seconds'] = processing_time
            result['method'] = method
            
            logger.info(f"PDF 처리 완료 ({method}): {processing_time:.2f}초")
            return {
                'status': 'success',
                'data': result,
                'processing_time_ms': int(processing_time * 1000)
            }
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"PDF 처리 실패 ({method}): {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'processing_time_ms': int(processing_time * 1000),
                'method': method
            }
    
    def _process_with_pymupdf(self, pdf_path: str, document_id: int) -> Dict:
        """PyMuPDF4LLM으로 처리 (Path 1)"""
        logger.info("Path 1: PyMuPDF4LLM 처리")
        return self.pymupdf_extractor.extract_full_document(
            pdf_path,
            document_id=document_id,
            save_images=True
        )
    
    async def _process_with_vision_async(self, pdf_path: str, document_id: int = None) -> Dict:
        """GPT-4 Vision으로 처리 (Path 2) - async 버전"""
        logger.info("Path 2: GPT-4 Vision 처리")
        return await self.vision_extractor.extract_full_document(
            pdf_path,
            document_id=document_id,
            save_images=True
        )
    
    async def _process_with_both_async(self, pdf_path: str, document_id: int) -> Dict:
        """
        진정한 하이브리드 처리: PyMuPDF 텍스트 + Vision API (텍스트를 컨텍스트로 활용)
        
        변경 사항:
        - 기존: PyMuPDF와 Vision을 독립적으로 실행 후 병합
        - 신규: PyMuPDF 텍스트를 Vision API의 input으로 제공하여 보완
        """
        logger.info("🔄 하이브리드 처리: PyMuPDF 텍스트 + Vision API")
        
        # Step 1: PyMuPDF로 텍스트 추출
        logger.info("Step 1: PyMuPDF 텍스트 추출")
        pymupdf_result = self._process_with_pymupdf(pdf_path, document_id)
        
        # Step 2: 페이지별 텍스트 추출 (Vision API에 컨텍스트로 제공)
        logger.info("Step 2: 페이지별 컨텍스트 준비")
        pages_data = pymupdf_result.get('pages', [])
        context_texts = [page['content'] for page in pages_data]
        
        logger.info(f"컨텍스트 준비 완료: {len(context_texts)}페이지")
        
        # Step 3: Vision API 호출 (하이브리드 모드 - 텍스트 컨텍스트 활용)
        logger.info("Step 3: Vision API 하이브리드 추출")
        vision_result = await self.vision_extractor.extract_with_context(
            pdf_path,
            context_texts=context_texts,
            apply_preprocessing=True,
            document_id=document_id,
            save_images=True
        )
        
        logger.info("Step 4: 하이브리드 결과 생성")
        
        # Vision 결과를 메인으로 사용 (텍스트 + 이미지 정보 모두 포함)
        # PyMuPDF 결과는 참고용으로 보관
        return {
            'markdown': vision_result['markdown'],
            'pages': vision_result.get('pages', []),  # ← pages 정보 추가
            'method': 'hybrid',  # 하이브리드 방식
            'metadata': {
                'total_pages': pymupdf_result['metadata'].get('total_pages', 0),
                'processing_time': (
                    pymupdf_result['metadata'].get('processing_time', 0) +
                    vision_result['metadata'].get('processing_time', 0)
                ),
                'hybrid_mode': True,
                'pymupdf_chars': pymupdf_result['metadata'].get('total_chars', 0),
                'vision_chars': vision_result['metadata'].get('total_chars', 0),
                'vision_tokens': vision_result['metadata'].get('total_tokens', 0),
                'table_count': pymupdf_result['metadata'].get('table_count', 0),
                'image_count': pymupdf_result['metadata'].get('image_count', 0),
            },
            # 디버깅용 원본 결과 포함
            'pymupdf_result': pymupdf_result,
            'vision_result': vision_result
        }
    
    def _save_markdown(
        self,
        markdown_text: str,
        pdf_path: str,
        document_id: int,
        method: str = "pymupdf"
    ) -> Path:
        """
        Markdown 파일 저장
        
        Args:
            markdown_text: Markdown 텍스트
            pdf_path: 원본 PDF 경로
            document_id: 문서 ID
            
        Returns:
            저장된 Markdown 파일 경로
        """
        pdf_path = Path(pdf_path)
        original_name = pdf_path.stem  # 이미 document_id 포함됨 (예: sample_policy_27)
        
        # uploads/documents/ 디렉토리에 저장
        # method 접미사 추가
        method_suffix = f"_{method}" if method != "pymupdf" else ""
        md_filename = f"{original_name}{method_suffix}.md"
        md_path = Path("uploads/documents") / md_filename
        
        # 디렉토리 생성
        md_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Markdown 저장
        md_path.write_text(markdown_text, encoding='utf-8')
        logger.info(f"Markdown 저장: {md_path}")
        
        return md_path
    
    def validate_pdf(self, pdf_path: str) -> bool:
        """
        PDF 파일 유효성 검사
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            유효 여부
        """
        path = Path(pdf_path)
        
        # 파일 존재 확인
        if not path.exists():
            logger.error(f"PDF 파일 없음: {pdf_path}")
            return False
        
        # 확장자 확인
        if path.suffix.lower() != '.pdf':
            logger.error(f"PDF 파일 아님: {pdf_path}")
            return False
        
        # 파일 크기 확인 (최소 1KB)
        if path.stat().st_size < 1024:
            logger.error(f"PDF 파일 크기 너무 작음: {pdf_path}")
            return False
        
        return True
    
    def _assign_vision_page_numbers(
        self,
        chunks: List,
        markdown_text: str,
        pages_info: List[Dict]
    ) -> List:
        """
        각 청크에 Vision의 page_number를 할당합니다.
        
        Args:
            chunks: 청크 리스트
            markdown_text: 전체 Markdown 텍스트
            pages_info: Vision의 페이지 정보
        
        Returns:
            page_number가 할당된 청크 리스트
        """
        from services.chunker import Chunk
        
        # 디버깅: 입력값 확인
        logger.info(f"=== page_number 할당 시작 ===")
        logger.info(f"청크 수: {len(chunks)}")
        logger.info(f"pages_info 수: {len(pages_info)}")
        logger.info(f"Markdown 길이: {len(markdown_text)}")
        logger.info(f"Markdown 앞부분 200자:\n{markdown_text[:200]}")
        
        # Markdown에서 "## 페이지 X" 위치 찾기
        page_positions = []
        for page_info in pages_info:
            vision_page_num = page_info['page_number']  # 1, 2, 3...
            pattern = f"## 페이지 {vision_page_num}"
            pos = markdown_text.find(pattern)
            
            logger.debug(f"패턴 '{pattern}' 검색 결과: pos={pos}")
            
            if pos >= 0:
                page_positions.append({
                    'vision_page_number': vision_page_num,
                    'position': pos
                })
            else:
                logger.warning(f"⚠️ 패턴 '{pattern}'을 Markdown에서 찾을 수 없습니다!")
        
        # 위치 기준 정렬
        page_positions.sort(key=lambda x: x['position'])
        
        logger.info(f"감지된 페이지 위치: {len(page_positions)}개")
        if page_positions:
            for pp in page_positions[:3]:
                logger.info(f"  - 페이지 {pp['vision_page_number']}: position {pp['position']}")
        
        if not page_positions:
            logger.error("❌ 페이지 위치를 하나도 찾지 못했습니다!")
            logger.error(f"Markdown 시작 500자:\n{markdown_text[:500]}")
            return chunks
        
        # 각 청크가 어느 Vision 페이지에 속하는지 판단
        success_count = 0
        fail_count = 0
        
        for chunk in chunks:
            # 청크의 위치 찾기 - 원본 그대로 검색 (정규화 없음)
            search_content = chunk.content[:100] if len(chunk.content) > 100 else chunk.content
            
            # 원본 Markdown에서 원본 청크 검색
            chunk_pos = markdown_text.find(search_content)
            
            # 실패 시 짧은 텍스트로 재시도
            if chunk_pos < 0 and len(search_content) > 50:
                search_content = search_content[:50]
                chunk_pos = markdown_text.find(search_content)
            
            if chunk_pos < 0:
                logger.warning(
                    f"⚠️ 청크 {chunk.chunk_index} 위치를 찾을 수 없음. "
                    f"검색 텍스트 앞 50자: '{search_content[:50]}'"
                )
                fail_count += 1
                continue
            
            # 청크보다 앞에 있는 가장 가까운 페이지 찾기
            current_page = None
            for page_info in reversed(page_positions):
                if page_info['position'] <= chunk_pos:
                    current_page = page_info['vision_page_number']
                    break
            
            # 페이지를 찾지 못한 경우, 첫 번째 페이지로 할당
            if current_page is None and page_positions:
                current_page = page_positions[0]['vision_page_number']
                logger.info(
                    f"청크 {chunk.chunk_index}가 첫 페이지보다 앞에 있음. "
                    f"첫 페이지({current_page})로 할당"
                )
            
            # 할당
            chunk.page_number = current_page
            
            if current_page:
                success_count += 1
                logger.debug(
                    f"✅ Chunk {chunk.chunk_index}: Vision page {current_page} "
                    f"(chunk_pos={chunk_pos})"
                )
            else:
                logger.warning(
                    f"⚠️ 청크 {chunk.chunk_index}의 페이지를 찾을 수 없음. "
                    f"chunk_pos={chunk_pos}"
                )
                fail_count += 1
        
        # 통계
        logger.info(f"=== page_number 할당 완료 ===")
        logger.info(f"✅ 성공: {success_count}개")
        logger.info(f"❌ 실패: {fail_count}개")
        if chunks:
            logger.info(f"📊 성공률: {success_count}/{len(chunks)} ({success_count*100/len(chunks):.1f}%)")
        
        return chunks
    
    async def _chunk_and_embed(
        self,
        markdown_text: str,
        document_id: int,
        db_session = None,
        pages_info: List[Dict] = None
    ) -> Dict:
        """
        Markdown 텍스트를 청킹하고 임베딩을 생성하며, DB에 저장합니다.
        
        Args:
            markdown_text: Markdown 텍스트
            document_id: 문서 ID
            db_session: 데이터베이스 세션 (optional)
            pages_info: Vision의 페이지 정보 (page_number 포함)
        
        Returns:
            청킹 및 임베딩 결과
        """
        logger.info("청킹 및 임베딩 시작")
        
        # 1. 텍스트 청킹
        logger.info("Step 1: 텍스트 청킹")
        chunks = self.chunker.chunk_markdown(
            markdown_text,
            document_id=document_id,
            extract_metadata=True
        )
        
        # 2. Vision page_number 할당
        if pages_info:
            logger.info("Step 2: Vision page_number 할당")
            chunks = self._assign_vision_page_numbers(chunks, markdown_text, pages_info)
        
        # 3. 임베딩 생성
        logger.info("Step 3: 임베딩 생성")
        chunks_with_embeddings = await self.embedding_service.create_chunk_embeddings(chunks)
        
        # 4. DB 저장 (세션이 제공된 경우)
        saved_count = 0
        if db_session:
            logger.info("Step 4: 벡터 DB 저장")
            from services.chunk_repository import ChunkRepository
            chunk_repo = ChunkRepository(db_session)
            
            try:
                saved_chunks = await chunk_repo.save_chunks(
                    chunks_with_embeddings,
                    document_id
                )
                saved_count = len(saved_chunks)
                logger.info(f"✅ DB 저장 완료: {saved_count}개 청크")
            except Exception as e:
                logger.error(f"❌ DB 저장 실패: {e}")
                logger.exception("상세 오류:")
                # DB 저장 실패 시 예외를 다시 발생시켜 상위에서 처리
                raise Exception(f"청크 DB 저장 실패: {e}")
        else:
            logger.warning("DB 세션이 제공되지 않아 저장을 건너뜁니다.")
        
        # 5. 결과 반환
        return {
            'total_chunks': len(chunks_with_embeddings),
            'text_chunks': sum(1 for c in chunks_with_embeddings if c.chunk_type == 'text'),
            'table_chunks': sum(1 for c in chunks_with_embeddings if c.chunk_type == 'table'),
            'total_tokens': sum(c.token_count for c in chunks_with_embeddings),
            'saved_to_db': saved_count > 0,
            'saved_count': saved_count,
            'chunks': [
                {
                    'chunk_index': c.chunk_index,
                    'chunk_type': c.chunk_type,
                    'content_preview': c.content[:100] + '...' if len(c.content) > 100 else c.content,
                    'token_count': c.token_count,
                    'page_number': c.page_number,
                    'pdf_page_number': c.pdf_page_number,
                    'section_title': c.section_title,
                    'clause_number': c.clause_number,
                    'has_embedding': 'embedding' in (c.metadata or {})
                }
                for c in chunks_with_embeddings
            ]
        }

