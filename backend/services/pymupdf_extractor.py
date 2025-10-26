"""
PyMuPDF4LLM을 사용한 PDF → Markdown 변환 서비스
Path 1: 직접 텍스트 추출
"""
import pymupdf4llm
import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import hashlib
import re
import logging

logger = logging.getLogger(__name__)


class PyMuPDFExtractor:
    """PyMuPDF4LLM 기반 PDF 추출기"""
    
    def __init__(self):
        """초기화"""
        self.supported_formats = ['.pdf']
    
    def extract_text_to_markdown(self, pdf_path: str) -> str:
        """
        PDF를 Markdown으로 변환
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            Markdown 텍스트
        """
        try:
            logger.info(f"PDF 변환 시작: {pdf_path}")
            
            # PyMuPDF4LLM으로 Markdown 변환
            # table_strategy=None: Markdown 표 생성 비활성화 (일반 텍스트로 표 추출)
            md_text = pymupdf4llm.to_markdown(
                pdf_path,
                table_strategy=None
            )
            
            # 후처리: Markdown 표 패턴 제거 (| ... | 형식)
            md_text = self._remove_markdown_tables(md_text)
            
            logger.info(f"PDF 변환 완료: {len(md_text)} 문자")
            return md_text
            
        except Exception as e:
            logger.error(f"PDF 변환 실패: {e}")
            raise
    
    def _remove_markdown_tables(self, markdown_text: str) -> str:
        """
        Markdown 텍스트에서 표 패턴(| ... |)을 제거합니다.
        
        Args:
            markdown_text: Markdown 텍스트
            
        Returns:
            표가 제거된 Markdown 텍스트
        """
        import re
        
        # Markdown 표 패턴 감지 및 제거
        # 패턴: |로 시작하고 |로 끝나는 연속된 줄들
        lines = markdown_text.split('\n')
        result_lines = []
        in_table = False
        
        for line in lines:
            stripped = line.strip()
            
            # 표 행 감지: |로 시작하고 |로 끝남
            if stripped.startswith('|') and stripped.endswith('|'):
                in_table = True
                # 표 라인은 건너뜀
                continue
            else:
                # 표가 아닌 줄
                if in_table:
                    # 표 종료 후 빈 줄 하나 추가 (간격 유지)
                    in_table = False
                result_lines.append(line)
        
        cleaned_text = '\n'.join(result_lines)
        
        # 연속된 빈 줄 3개 이상을 2개로 축소
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        
        return cleaned_text
    
    def detect_tables(self, markdown_text: str) -> List[Dict]:
        """
        Markdown 텍스트에서 표 감지
        
        Args:
            markdown_text: Markdown 텍스트
            
        Returns:
            표 정보 리스트
        """
        tables = []
        
        # '|'로 시작하는 표 형식 감지
        lines = markdown_text.split('\n')
        table_start = None
        table_lines = []
        
        for idx, line in enumerate(lines):
            # 표 행 감지 (|로 시작하고 |로 끝남)
            if line.strip().startswith('|') and line.strip().endswith('|'):
                if table_start is None:
                    table_start = idx
                table_lines.append(line)
            else:
                # 표 끝
                if table_start is not None and len(table_lines) >= 2:
                    table_content = '\n'.join(table_lines)
                    tables.append({
                        'start_line': table_start,
                        'end_line': idx - 1,
                        'content': table_content,
                        'row_count': len(table_lines) - 1,  # 헤더 제외
                        'hash': hashlib.md5(table_content.encode()).hexdigest()
                    })
                table_start = None
                table_lines = []
        
        # 마지막 표 처리
        if table_start is not None and len(table_lines) >= 2:
            table_content = '\n'.join(table_lines)
            tables.append({
                'start_line': table_start,
                'end_line': len(lines) - 1,
                'content': table_content,
                'row_count': len(table_lines) - 1,
                'hash': hashlib.md5(table_content.encode()).hexdigest()
            })
        
        logger.info(f"표 감지 완료: {len(tables)}개")
        return tables
    
    def detect_images(
        self, 
        pdf_path: str, 
        markdown_text: str,
        save_images: bool = False,
        document_id: Optional[int] = None
    ) -> List[Dict]:
        """
        PDF에서 이미지 추출 및 메타데이터 생성
        
        Args:
            pdf_path: PDF 파일 경로
            markdown_text: Markdown 텍스트 (이미지 참조용)
            save_images: 이미지 파일 저장 여부
            document_id: 문서 ID (이미지 저장 시 필요)
            
        Returns:
            이미지 정보 리스트
        """
        from pathlib import Path
        from PIL import Image
        import io
        
        images = []
        
        # 이미지 저장 디렉토리 생성
        if save_images and document_id is not None:
            image_dir = Path("uploads/images") / str(document_id)
            image_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"이미지 저장 디렉토리: {image_dir}")
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]  # 이미지 참조 번호
                    
                    # 이미지 메타데이터
                    image_info = {
                        'page_number': page_num + 1,
                        'image_index': img_index,
                        'xref': xref,
                        'width': img[2],
                        'height': img[3],
                    }
                    
                    # 이미지 저장
                    if save_images and document_id is not None:
                        try:
                            # 이미지 추출
                            img_data = doc.extract_image(xref)
                            img_bytes = img_data["image"]
                            img_ext = img_data["ext"]  # 원본 형식 (png, jpeg 등)
                            
                            # PIL Image로 변환하여 PNG로 저장
                            pil_image = Image.open(io.BytesIO(img_bytes))
                            
                            # 저장 경로
                            img_filename = f"page_{page_num + 1}_img_{img_index + 1}.png"
                            img_path = image_dir / img_filename
                            
                            # PNG로 저장
                            pil_image.save(img_path, "PNG")
                            
                            # 저장된 파일 정보 추가
                            image_info['saved_path'] = str(img_path)
                            image_info['filename'] = img_filename
                            image_info['original_format'] = img_ext
                            
                            logger.debug(f"이미지 저장: {img_path}")
                        
                        except Exception as e:
                            logger.error(f"이미지 저장 실패 (page {page_num + 1}, img {img_index}): {e}")
                            image_info['save_error'] = str(e)
                    
                    images.append(image_info)
            
            doc.close()
            logger.info(f"이미지 감지 완료: {len(images)}개")
            
        except Exception as e:
            logger.error(f"이미지 추출 실패: {e}")
        
        return images
    
    def extract_by_pages(self, pdf_path: str) -> List[Dict]:
        """
        PDF를 페이지별로 추출 및 구조화
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            페이지별 데이터 리스트
        """
        pages_data = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # 페이지별 Markdown 변환
                # table_strategy=None: Markdown 표 생성 비활성화 (일반 텍스트로 표 추출)
                page_md = pymupdf4llm.to_markdown(
                    pdf_path,
                    pages=[page_num],
                    table_strategy=None
                )
                
                # 후처리: Markdown 표 패턴 제거
                page_md = self._remove_markdown_tables(page_md)
                
                # 페이지 데이터 구조화
                page_data = {
                    'page_number': page_num + 1,
                    'content': page_md,
                    'content_hash': hashlib.md5(page_md.encode()).hexdigest(),
                    'char_count': len(page_md),
                    'width': page.rect.width,
                    'height': page.rect.height,
                }
                
                pages_data.append(page_data)
            
            doc.close()
            logger.info(f"페이지별 추출 완료: {len(pages_data)}페이지")
            
        except Exception as e:
            logger.error(f"페이지별 추출 실패: {e}")
            raise
        
        return pages_data
    
    def extract_full_document(
        self, 
        pdf_path: str,
        document_id: Optional[int] = None,
        save_images: bool = True
    ) -> Dict:
        """
        PDF 전체 문서 추출 (메인 함수)
        
        Args:
            pdf_path: PDF 파일 경로
            document_id: 문서 ID (이미지 저장 시 필요)
            save_images: 이미지 파일 저장 여부
            
        Returns:
            전체 문서 데이터
        """
        logger.info(f"PDF 전체 문서 추출 시작: {pdf_path}")
        
        # 1. 페이지별 데이터 추출 (먼저 수행)
        pages = self.extract_by_pages(pdf_path)
        
        # 2. 페이지별 Markdown을 "## 페이지 X" 마커와 함께 결합
        markdown_parts = []
        for page in pages:
            page_num = page['page_number']
            page_content = page['content'].strip()
            
            # 페이지 마커 추가 (Vision API와 동일한 형식)
            markdown_parts.append(f"## 페이지 {page_num}\n\n{page_content}")
        
        # 전체 Markdown 생성
        full_markdown = "\n\n".join(markdown_parts)
        
        logger.info(f"페이지 마커 추가 완료: {len(pages)}페이지")
        
        # 3. 표 감지
        tables = self.detect_tables(full_markdown)
        
        # 4. 이미지 감지 및 저장
        images = self.detect_images(
            pdf_path, 
            full_markdown,
            save_images=save_images,
            document_id=document_id
        )
        
        # 5. 문서 메타데이터
        doc_metadata = {
            'total_pages': len(pages),
            'total_chars': len(full_markdown),
            'table_count': len(tables),
            'image_count': len(images),
            'content_hash': hashlib.md5(full_markdown.encode()).hexdigest(),
        }
        
        result = {
            'markdown': full_markdown,
            'tables': tables,
            'images': images,
            'pages': pages,
            'metadata': doc_metadata,
        }
        
        logger.info(f"PDF 전체 문서 추출 완료: {doc_metadata}")
        return result

