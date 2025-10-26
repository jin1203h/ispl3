"""
GPT-4 Vision 추출 기능 테스트 스크립트
"""
import sys
from pathlib import Path
import asyncio

# backend 루트를 Python 경로에 추가
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from services.vision_extractor import VisionExtractor
from services.pdf_processor import PDFProcessor
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_vision_extraction():
    """Vision 추출 테스트"""
    logger.info("=" * 60)
    logger.info("GPT-4 Vision 추출 기능 테스트 시작")
    logger.info("=" * 60)
    
    # Vision 추출기 생성
    extractor = VisionExtractor()
    
    # 테스트용 PDF 파일 경로 입력 받기
    print("\n테스트할 PDF 파일 경로를 입력하세요:")
    print("(예: D:\\sample.pdf)")
    print("⚠️  주의: GPT-4 Vision API를 사용하므로 비용이 발생합니다.")
    pdf_path = input("PDF 경로: ").strip()
    
    if not pdf_path:
        logger.error("PDF 경로가 입력되지 않았습니다.")
        return
    
    if not Path(pdf_path).exists():
        logger.error(f"파일을 찾을 수 없습니다: {pdf_path}")
        return
    
    # 처리 방법 선택
    print("\n처리 방법을 선택하세요:")
    print("1. 첫 페이지만 테스트 (빠름)")
    print("2. 전체 문서 처리 (느리고 비용 발생)")
    choice = input("선택 (1 또는 2): ").strip()
    
    try:
        if choice == "1":
            # 첫 페이지만 테스트
            logger.info(f"\n첫 페이지 추출 시작: {pdf_path}")
            
            # PDF → 이미지 변환
            images = extractor.pdf_to_images(pdf_path)
            logger.info(f"총 {len(images)}페이지 중 첫 페이지만 처리합니다.")
            
            # 첫 페이지만 추출
            result = await extractor.extract_text_from_image(images[0], 1)
            
            # 결과 출력
            print("\n" + "=" * 60)
            print("추출 결과")
            print("=" * 60)
            print(f"\n📄 페이지 {result['page_number']}")
            print(f"🤖 모델: {result['model']}")
            print(f"🎫 토큰 사용: {result['tokens_used']['total']}")
            print("\n📋 추출된 내용:")
            print("-" * 60)
            print(result['content'])
            print("-" * 60)
            
        elif choice == "2":
            # 전체 문서 처리
            logger.info(f"\n전체 문서 추출 시작: {pdf_path}")
            
            result = await extractor.extract_full_document(pdf_path)
            metadata = result['metadata']
            
            # 결과 출력
            print("\n" + "=" * 60)
            print("추출 결과")
            print("=" * 60)
            print(f"\n✅ 처리 성공!")
            print(f"📄 총 페이지 수: {metadata['total_pages']}")
            print(f"📝 총 문자 수: {metadata['total_chars']:,}")
            print(f"🎫 총 토큰 사용: {metadata['total_tokens']:,}")
            print(f"🤖 모델: {metadata['model']}")
            print(f"📐 DPI: {metadata['dpi']}")
            
            # Markdown 미리보기
            markdown = result['markdown']
            preview_length = 500
            print(f"\n📋 Markdown 미리보기 (처음 {preview_length}자):")
            print("-" * 60)
            print(markdown[:preview_length])
            if len(markdown) > preview_length:
                print(f"... (총 {len(markdown)}자 중 {preview_length}자 표시)")
            print("-" * 60)
            
            # 페이지별 토큰 사용량
            print(f"\n🎫 페이지별 토큰 사용량:")
            for page in result['pages'][:5]:  # 처음 5페이지만
                print(f"  페이지 {page['page_number']}: {page['tokens_used']['total']} 토큰")
            if len(result['pages']) > 5:
                print(f"  ... (총 {len(result['pages'])}페이지)")
        
        else:
            print("잘못된 선택입니다.")
            return
        
        logger.info("\n" + "=" * 60)
        logger.info("테스트 완료")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"테스트 실패: {e}", exc_info=True)


def test_with_processor():
    """PDF Processor를 통한 테스트"""
    logger.info("=" * 60)
    logger.info("PDF Processor (Vision) 테스트")
    logger.info("=" * 60)
    
    processor = PDFProcessor()
    
    print("\n테스트할 PDF 파일 경로를 입력하세요:")
    pdf_path = input("PDF 경로: ").strip()
    
    if not pdf_path or not Path(pdf_path).exists():
        logger.error("유효하지 않은 PDF 경로")
        return
    
    # Vision 방법으로 처리
    result = processor.process_pdf(
        pdf_path=pdf_path,
        document_id=2,  # 테스트용 ID
        save_markdown=True,
        method="vision"
    )
    
    if result['status'] == 'success':
        data = result['data']
        metadata = data['metadata']
        
        print(f"\n✅ 처리 성공!")
        print(f"📄 총 페이지 수: {metadata['total_pages']}")
        print(f"📝 총 문자 수: {metadata['total_chars']:,}")
        print(f"🎫 총 토큰 사용: {metadata['total_tokens']:,}")
        print(f"⏱️  처리 시간: {result['processing_time_ms']/1000:.2f}초")
        
        if 'markdown_path' in data:
            print(f"💾 Markdown 저장: {data['markdown_path']}")
    else:
        print(f"\n❌ 처리 실패: {result.get('error')}")


if __name__ == "__main__":
    print("\n테스트 모드 선택:")
    print("1. Vision Extractor 직접 테스트 (권장)")
    print("2. PDF Processor 통합 테스트")
    
    mode = input("선택 (1 또는 2): ").strip()
    
    try:
        if mode == "1":
            asyncio.run(test_vision_extraction())
        elif mode == "2":
            test_with_processor()
        else:
            print("잘못된 선택입니다.")
    except KeyboardInterrupt:
        print("\n\n테스트 중단")
    except Exception as e:
        logger.error(f"테스트 오류: {e}", exc_info=True)

