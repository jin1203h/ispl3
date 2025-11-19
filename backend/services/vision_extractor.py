"""
GPT-4 Vision을 사용한 PDF 텍스트 추출 서비스
"""
import asyncio
import base64
import io
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from io import BytesIO

import fitz  # PyMuPDF for PDF to image conversion
from PIL import Image
from openai import AsyncOpenAI
import tenacity

from pdf2image import convert_from_path

from core.config import settings
from core.poppler_config import POPPLER_PATH
from services.image_preprocessor import ImagePreprocessor

logger = logging.getLogger(__name__)


class VisionExtractor:
    """GPT-4 Vision API를 사용한 텍스트 추출"""
    
    def __init__(self):
        """초기화"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.preprocessor = ImagePreprocessor()
        self.model = "gpt-4o"  # GPT-4 with vision
        self.dpi = 300
        self.max_retries = 3
    
    async def pdf_to_images(
        self,
        pdf_path: str,
        dpi: int = 300,
        document_id: Optional[int] = None,
        save_images: bool = True
    ) -> List[Image.Image]:
        """
        PDF 파일을 이미지로 변환합니다.
        
        Args:
            pdf_path: PDF 파일 경로
            dpi: 이미지 해상도 (Dots Per Inch)
            document_id: 문서 ID (이미지 저장 시 필요)
            save_images: 이미지 파일 저장 여부
            
        Returns:
            PIL Image 리스트
        """
        dpi = dpi or self.dpi
        logger.info(f"PDF → 이미지 변환 시작: {pdf_path} (DPI={dpi})")
        
        try:
            images = convert_from_path(
                pdf_path,
                dpi=dpi,
                fmt='png',
                poppler_path=POPPLER_PATH  # Windows Poppler 경로 지원
            )
            logger.info(f"이미지 변환 완료: {len(images)}페이지")
            
            # 이미지 저장 (옵션)
            if save_images and document_id is not None:
                await self._save_images(images, document_id)
            
            return images
        
        except Exception as e:
            logger.error(f"PDF → 이미지 변환 실패: {e}")
            if "poppler" in str(e).lower():
                logger.error(
                    "Poppler가 설치되지 않았습니다. "
                    "Windows: https://github.com/oschwartz10612/poppler-windows/releases 에서 다운로드하거나 "
                    "환경 변수 POPPLER_PATH를 설정하세요."
                )
            raise
    
    async def _save_images(
        self,
        images: List[Image.Image],
        document_id: int
    ) -> List[str]:
        """
        변환된 이미지를 파일로 저장합니다.
        
        Args:
            images: PIL Image 리스트
            document_id: 문서 ID
            
        Returns:
            저장된 이미지 경로 리스트
        """
        from pathlib import Path
        
        # 이미지 저장 디렉토리 생성
        image_dir = Path("uploads/images") / str(document_id)
        image_dir.mkdir(parents=True, exist_ok=True)
        
        saved_paths = []
        
        logger.info(f"이미지 저장 시작: {len(images)}페이지 → {image_dir}")
        
        for page_num, image in enumerate(images, start=1):
            try:
                # 파일명: page_1.png, page_2.png, ...
                filename = f"page_{page_num}.png"
                file_path = image_dir / filename
                
                # PNG로 저장
                image.save(file_path, "PNG")
                saved_paths.append(str(file_path))
                
                # 100페이지마다 로그
                if page_num % 100 == 0:
                    logger.info(f"이미지 저장 진행: {page_num}/{len(images)}페이지")
            
            except Exception as e:
                logger.error(f"페이지 {page_num} 이미지 저장 실패: {e}")
        
        logger.info(f"이미지 저장 완료: {len(saved_paths)}개 파일")
        return saved_paths
    
    def preprocess_image(
        self,
        image: Image.Image,
        apply_preprocessing: bool = True
    ) -> Image.Image:
        """
        이미지 전처리
        
        Args:
            image: PIL Image
            apply_preprocessing: 전처리 적용 여부
            
        Returns:
            전처리된 PIL Image
        """
        if not apply_preprocessing:
            return image
        
        # numpy array로 변환 후 전처리
        np_image = self.preprocessor.pil_to_numpy(image)
        
        # 전처리 적용
        processed = self.preprocessor.preprocess(
            np_image,
            apply_grayscale=False,  # 컬러 유지 (Vision API 최적화)
            apply_noise_removal=True,
            apply_deskew=False  # 성능 고려하여 기본 비활성화
        )
        
        # PIL Image로 변환
        return self.preprocessor.numpy_to_pil(processed)
    
    def image_to_base64(self, image: Image.Image) -> str:
        """
        PIL Image를 base64 문자열로 변환
        
        Args:
            image: PIL Image
            
        Returns:
            base64 인코딩된 문자열
        """
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        img_bytes = buffer.getvalue()
        return base64.b64encode(img_bytes).decode('utf-8')
    
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        retry=tenacity.retry_if_exception_type(Exception),
        before_sleep=lambda retry_state: logger.warning(
            f"재시도 {retry_state.attempt_number}/3"
        )
    )
    async def extract_text_from_image(
        self,
        image: Image.Image,
        page_number: int,
        context_text: Optional[str] = None
    ) -> Dict:
        """
        GPT-4 Vision으로 이미지에서 텍스트 추출
        
        Args:
            image: PIL Image
            page_number: 페이지 번호
            context_text: PyMuPDF에서 추출한 컨텍스트 텍스트 (하이브리드 모드)
            
        Returns:
            추출 결과
        """
        logger.info(f"페이지 {page_number} 텍스트 추출 시작 (context={'있음' if context_text else '없음'})")
        
        # 이미지를 base64로 인코딩
        img_base64 = self.image_to_base64(image)
        
        # 프롬프트 생성 (하이브리드 모드 vs 일반 모드)
        if context_text:
            # 하이브리드 모드: 텍스트 컨텍스트 활용
            prompt_text = f"""다음은 이 페이지에서 추출된 텍스트입니다:

---
{context_text}
---

위 텍스트를 **참고하여**, 이미지의 내용을 검증하고 보완해주세요.

**작업 지침:**
1. **페이지 번호 추출 (최우선):**
   - 페이지 상단/하단에 인쇄된 페이지 번호가 있다면 반드시 다음 형식으로 맨 앞에 표시:
     ### [페이지번호]
   - 예시: ### 3
   - 페이지 번호가 없으면 생략하세요
2. 텍스트 내용이 정확한지 이미지로 확인
3. **표 구조와 데이터**를 이미지 기반으로 정확히 검증 및 보완
4. **이미지/도식/그림**이 있다면 상세히 설명:
   - 이미지 내 모든 텍스트, 라벨, 번호 추출
   - 도식의 구조와 요소 간 관계 (화살표, 연결선 등)
   - 해부학적 도식인 경우 각 부위의 명칭과 위치
   - 이미지가 문서 내용과의 관계
   - 형식: [이미지 상세 설명:\\n내용...\\n]
5. 레이아웃 정보 (들여쓰기, 목록 구조 등) 보완
6. 특수 문자나 기호가 누락되었다면 추가

**출력 형식:**
- Markdown 형식으로 작성
- 페이지 번호가 있다면 맨 앞에 ### 형식으로 표시
- 조항 번호, 제목, 내용을 명확히 구분
- 표는 Markdown 표 형식 (|)으로 작성"""
        else:
            # 일반 모드: 이미지만으로 추출
            prompt_text = """이 보험 약관 페이지의 모든 내용을 Markdown 형식으로 변환해주세요.

다음 사항을 포함하세요:
1. **페이지 번호 추출 (최우선):**
   - 페이지 상단/하단에 인쇄된 페이지 번호가 있다면 반드시 다음 형식으로 맨 앞에 표시:
     ### [페이지번호]
   - 예시: ### 3
   - 페이지 번호가 없으면 생략하세요
2. 모든 텍스트 (제목, 본문, 각주 등)
3. 표는 Markdown 표 형식 (|)으로 변환
4. **이미지는 반드시 상세히 설명**:
   - 이미지 내 모든 텍스트, 라벨, 번호를 추출
   - 도식의 구조와 요소 간 관계 설명 (예: 화살표, 연결선)
   - 해부학적 도식인 경우 각 부위의 명칭과 위치 설명
   - 이미지가 문서에서 설명하는 내용과의 관계
   - 형식: [이미지 상세 설명:\n내용...\n]
5. 페이지 레이아웃과 구조를 최대한 유지

**중요: 페이지에 인쇄된 페이지 번호가 있다면 출력의 맨 앞에 ### [페이지번호] 형식으로 반드시 표시하세요!**

조항 번호, 제목, 내용을 정확히 구분하여 작성하세요."""
        
        # GPT-4 Vision API 호출
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 보험 약관 문서를 정확하게 텍스트로 변환하는 전문가입니다. 표, 이미지, 모든 텍스트를 빠짐없이 Markdown 형식으로 변환하세요."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt_text
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=8192,  # 이미지 상세 설명을 위해 증가
                temperature=0.1  # 정확성을 위해 낮은 temperature
            )
            
            extracted_text = response.choices[0].message.content
            
            # Markdown 코드 블록 마커 제거 (```markdown ... ``` 형태)
            if extracted_text:
                # 앞뒤 공백 제거
                extracted_text = extracted_text.strip()
                
                # ```markdown 으로 시작하는 경우
                if extracted_text.startswith('```markdown'):
                    extracted_text = extracted_text[len('```markdown'):].lstrip('\n')
                # ``` 으로 시작하는 경우
                elif extracted_text.startswith('```'):
                    extracted_text = extracted_text[3:].lstrip('\n')
                
                # ``` 으로 끝나는 경우
                if extracted_text.endswith('```'):
                    extracted_text = extracted_text[:-3].rstrip('\n')
                
                # 최종 공백 정리
                extracted_text = extracted_text.strip()
            
            result = {
                'page_number': page_number,
                'content': extracted_text,
                'model': self.model,
                'has_context': context_text is not None,
                'tokens_used': {
                    'prompt': response.usage.prompt_tokens,
                    'completion': response.usage.completion_tokens,
                    'total': response.usage.total_tokens
                }
            }
            
            logger.info(
                f"페이지 {page_number} 추출 완료: "
                f"{len(extracted_text)} 문자, "
                f"{response.usage.total_tokens} 토큰"
            )
            return result
        
        except Exception as e:
            logger.error(f"페이지 {page_number} 추출 실패: {e}")
            raise
    
    async def extract_batch(
        self,
        images: List[Image.Image],
        start_page: int = 1,
        context_texts: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        여러 이미지를 병렬로 처리
        
        Args:
            images: PIL Image 리스트
            start_page: 시작 페이지 번호
            context_texts: 페이지별 컨텍스트 텍스트 리스트 (하이브리드 모드)
            
        Returns:
            추출 결과 리스트
        """
        logger.info(
            f"배치 처리 시작: {len(images)}페이지 "
            f"(context={'있음' if context_texts else '없음'})"
        )
        
        # Semaphore로 동시 요청 수 제한 (OpenAI API rate limit 고려)
        semaphore = asyncio.Semaphore(50)  # 최대 50개 동시 요청 (3 → 50 최적화)
        
        async def process_with_semaphore(
            image: Image.Image, 
            page_num: int, 
            context: Optional[str] = None
        ):
            async with semaphore:
                return await self.extract_text_from_image(image, page_num, context)
        
        # 모든 페이지를 병렬 처리
        tasks = []
        for idx, img in enumerate(images):
            page_num = start_page + idx
            context = None
            if context_texts and idx < len(context_texts):
                context = context_texts[idx]
            tasks.append(process_with_semaphore(img, page_num, context))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 성공한 결과만 필터링
        successful_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"페이지 {start_page + idx} 처리 실패: {result}")
            else:
                successful_results.append(result)
        
        logger.info(f"배치 처리 완료: {len(successful_results)}/{len(images)} 성공")
        return successful_results
    
    async def extract_full_document(
        self,
        pdf_path: str,
        apply_preprocessing: bool = True,
        max_concurrent: int = 3,
        document_id: Optional[int] = None,
        save_images: bool = True
    ) -> Dict:
        """
        PDF 전체 문서 추출 (메인 함수)
        
        Args:
            pdf_path: PDF 파일 경로
            apply_preprocessing: 이미지 전처리 적용 여부
            max_concurrent: 최대 동시 처리 수
            document_id: 문서 ID (이미지 저장 시 필요)
            save_images: 이미지 파일 저장 여부
            
        Returns:
            추출 결과
        """
        from datetime import datetime
        start_time = datetime.now()
        
        logger.info(f"GPT-4 Vision 추출 시작: {pdf_path}")
        
        # 1. PDF를 이미지로 변환 (및 저장)
        images = await self.pdf_to_images(
            pdf_path,
            document_id=document_id,
            save_images=save_images
        )
        
        # 2. 이미지 전처리 (옵션)
        if apply_preprocessing:
            logger.info("이미지 전처리 적용")
            images = [self.preprocess_image(img) for img in images]
        
        # 3. 배치 처리
        results = await self.extract_batch(images)
        
        # 4. 결과 병합
        pages = []
        total_tokens = 0
        
        for result in sorted(results, key=lambda x: x['page_number']):
            pages.append({
                'page_number': result['page_number'],
                'content': result['content']
            })
            total_tokens += result['tokens_used']['total']
        
        # Markdown으로 병합
        markdown_parts = []
        for page in pages:
            markdown_parts.append(f"## 페이지 {page['page_number']}\n")
            markdown_parts.append(page['content'])
            markdown_parts.append("\n---\n")
        
        full_markdown = "\n".join(markdown_parts)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(
            f"GPT-4 Vision 추출 완료: {len(pages)}페이지, "
            f"{total_tokens} 토큰, {processing_time:.2f}초"
        )
        
        return {
            'markdown': full_markdown,
            'pages': pages,
            'metadata': {
                'processing_time': processing_time,
                'total_pages': len(pages),
                'total_chars': len(full_markdown),
                'total_tokens': total_tokens,
                'model': self.model,
                'dpi': self.dpi,
            }
        }
    
    async def extract_with_context(
        self,
        pdf_path: str,
        context_texts: List[str],
        apply_preprocessing: bool = True,
        document_id: Optional[int] = None,
        save_images: bool = True
    ) -> Dict:
        """
        하이브리드 방식: PyMuPDF 텍스트를 컨텍스트로 활용한 Vision 추출
        
        Args:
            pdf_path: PDF 파일 경로
            context_texts: 페이지별 PyMuPDF 추출 텍스트 리스트
            apply_preprocessing: 이미지 전처리 적용 여부
            document_id: 문서 ID (이미지 저장 시 필요)
            save_images: 이미지 파일 저장 여부
            
        Returns:
            추출 결과
        """
        from datetime import datetime
        start_time = datetime.now()
        
        logger.info(
            f"🔄 하이브리드 Vision 추출 시작: {pdf_path} "
            f"(컨텍스트: {len(context_texts)}페이지)"
        )
        
        # 1. PDF를 이미지로 변환 (및 저장)
        images = await self.pdf_to_images(
            pdf_path,
            document_id=document_id,
            save_images=save_images
        )
        
        # 페이지 수 검증
        if len(images) != len(context_texts):
            logger.warning(
                f"페이지 수 불일치: 이미지={len(images)}, "
                f"컨텍스트={len(context_texts)}"
            )
        
        # 2. 이미지 전처리 (옵션)
        if apply_preprocessing:
            logger.info("이미지 전처리 적용")
            images = [self.preprocess_image(img) for img in images]
        
        # 3. 하이브리드 배치 처리 (컨텍스트 텍스트 활용)
        results = await self.extract_batch(
            images, 
            start_page=1,
            context_texts=context_texts
        )
        
        # 4. 결과 병합
        pages = []
        total_tokens = 0
        
        for result in sorted(results, key=lambda x: x['page_number']):
            pages.append({
                'page_number': result['page_number'],
                'content': result['content'],
                'has_context': result.get('has_context', False)
            })
            total_tokens += result['tokens_used']['total']
        
        # Markdown으로 병합
        markdown_parts = []
        for page in pages:
            markdown_parts.append(f"## 페이지 {page['page_number']}\n")
            markdown_parts.append(page['content'])
            markdown_parts.append("\n---\n")
        
        full_markdown = "\n".join(markdown_parts)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(
            f"✅ 하이브리드 Vision 추출 완료: {len(pages)}페이지, "
            f"{total_tokens} 토큰, {processing_time:.2f}초"
        )
        
        return {
            'markdown': full_markdown,
            'pages': pages,
            'metadata': {
                'processing_time': processing_time,
                'total_pages': len(pages),
                'total_chars': len(full_markdown),
                'total_tokens': total_tokens,
                'model': self.model,
                'dpi': self.dpi,
                'hybrid_mode': True,
                'context_pages': len(context_texts)
            }
        }

