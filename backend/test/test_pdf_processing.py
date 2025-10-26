"""
PDF 처리 기능 테스트 스크립트
"""
import sys
from pathlib import Path

# backend 루트를 Python 경로에 추가 (test 폴더 → backend 폴더)
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from services.pdf_processor import PDFProcessor
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_pdf_processing():
    """PDF 처리 테스트"""
    logger.info("=" * 60)
    logger.info("PDF 처리 기능 테스트 시작")
    logger.info("=" * 60)
    
    # PDF 프로세서 생성
    processor = PDFProcessor()
    
    # 테스트용 PDF 파일 경로 입력 받기
    print("\n테스트할 PDF 파일 경로를 입력하세요:")
    print("(예: D:\\sample.pdf 또는 상대 경로)")
    pdf_path = input("PDF 경로: ").strip()
    
    if not pdf_path:
        logger.error("PDF 경로가 입력되지 않았습니다.")
        return
    
    # 파일 유효성 검사
    if not processor.validate_pdf(pdf_path):
        logger.error("유효하지 않은 PDF 파일입니다.")
        return
    
    # PDF 처리
    logger.info(f"\nPDF 처리 시작: {pdf_path}")
    result = processor.process_pdf(
        pdf_path=pdf_path,
        document_id=1,  # 테스트용 ID
        save_markdown=True
    )
    
    # 결과 출력
    logger.info("\n" + "=" * 60)
    logger.info("처리 결과")
    logger.info("=" * 60)
    
    if result['status'] == 'success':
        data = result['data']
        metadata = data['metadata']
        
        print(f"\n✅ 처리 성공!")
        print(f"📄 총 페이지 수: {metadata['total_pages']}")
        print(f"📝 총 문자 수: {metadata['total_chars']:,}")
        print(f"📊 표 개수: {metadata['table_count']}")
        print(f"🖼️  이미지 개수: {metadata['image_count']}")
        print(f"⏱️  처리 시간: {result['processing_time_ms']/1000:.2f}초")
        
        if 'markdown_path' in data:
            print(f"💾 Markdown 저장: {data['markdown_path']}")
        
        # Markdown 미리보기
        markdown = data['markdown']
        preview_length = 500
        print(f"\n📋 Markdown 미리보기 (처음 {preview_length}자):")
        print("-" * 60)
        print(markdown[:preview_length])
        if len(markdown) > preview_length:
            print(f"... (총 {len(markdown)}자 중 {preview_length}자 표시)")
        print("-" * 60)
        
        # 표 정보
        if data['tables']:
            print(f"\n📊 감지된 표 정보:")
            for idx, table in enumerate(data['tables'][:3], 1):  # 최대 3개만 표시
                print(f"  표 {idx}: {table['row_count']}행, 라인 {table['start_line']}-{table['end_line']}")
        
        # 이미지 정보
        if data['images']:
            print(f"\n🖼️  감지된 이미지 정보:")
            for idx, img in enumerate(data['images'][:3], 1):  # 최대 3개만 표시
                print(f"  이미지 {idx}: 페이지 {img['page_number']}, 크기 {img['width']}x{img['height']}")
    
    else:
        print(f"\n❌ 처리 실패: {result.get('error')}")
    
    logger.info("\n" + "=" * 60)
    logger.info("테스트 완료")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        test_pdf_processing()
    except KeyboardInterrupt:
        print("\n\n테스트 중단")
    except Exception as e:
        logger.error(f"테스트 오류: {e}", exc_info=True)

