"""
하이브리드 병합 기능 테스트
Path 1(PyMuPDF)과 Path 2(GPT-4 Vision)의 결과를 병합하고 품질을 검증합니다.
"""
import sys
from pathlib import Path
import logging

# backend 루트를 Python 경로에 추가
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from services.pdf_processor import PDFProcessor

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title: str):
    """섹션 제목 출력"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_quality_report(quality: dict):
    """품질 리포트 출력"""
    print(f"\n📊 품질 평가 결과:")
    print(f"  - 완전성 (Completeness): {quality['completeness']:.2%}")
    print(f"  - 일관성 (Consistency):  {quality['consistency']:.2%}")
    print(f"  - 정확도 (Accuracy):      {quality['accuracy']:.2%}")
    print(f"  - 종합 점수:              {quality['overall_score']:.2%}")
    print(f"  - 상태:                   {quality['status']}")
    
    if quality['issues']:
        print(f"\n⚠️ 발견된 문제:")
        for issue in quality['issues']:
            print(f"  - {issue}")


def test_hybrid_merge():
    """하이브리드 병합 기능 테스트"""
    print_section("하이브리드 병합 기능 테스트")
    
    # PDF 경로 입력
    print("\n테스트할 PDF 파일 경로를 입력하세요:")
    print("(예: D:\\sample.pdf)")
    print("⚠️  주의: 'both' 방법은 GPT-4 Vision API를 사용하므로 비용이 발생합니다.")
    pdf_path = input("PDF 경로: ").strip()
    
    if not Path(pdf_path).exists():
        logger.error(f"파일을 찾을 수 없습니다: {pdf_path}")
        return
    
    # PDF Processor 초기화
    processor = PDFProcessor()
    
    # 유효성 검사
    if not processor.validate_pdf(pdf_path):
        logger.error("유효하지 않은 PDF 파일입니다.")
        return
    
    # 테스트 모드 선택
    print("\n처리 방법을 선택하세요:")
    print("1. PyMuPDF만 (Path 1)")
    print("2. Vision만 (Path 2, 비용 발생)")
    print("3. 하이브리드 (Path 1 + Path 2, 비용 발생)")
    choice = input("선택 (1, 2 또는 3): ").strip()
    
    method_map = {
        "1": "pymupdf",
        "2": "vision",
        "3": "both"
    }
    method = method_map.get(choice, "pymupdf")
    
    # 처리 시작
    print_section(f"PDF 처리 시작 (method={method})")
    logger.info(f"처리 시작: {pdf_path}")
    
    try:
        result = processor.process_pdf(
            pdf_path,
            document_id=999,  # 테스트용 ID
            save_markdown=True,
            method=method
        )
        
        if result['status'] == 'success':
            data = result['data']
            print(f"\n✅ 처리 성공!")
            print(f"  - 처리 시간: {result['processing_time_ms']}ms")
            print(f"  - 사용된 방법: {data.get('method', method)}")
            
            # 메타데이터 출력
            metadata = data.get('metadata', {})
            print(f"\n📄 문서 정보:")
            print(f"  - 총 페이지: {metadata.get('total_pages', 'N/A')}")
            print(f"  - 처리 시간: {metadata.get('processing_time', 'N/A'):.2f}초")
            
            # 하이브리드 결과인 경우
            if method == "both":
                print(f"\n🔀 하이브리드 병합 정보:")
                print(f"  - 유사도: {metadata.get('similarity', 0):.2%}")
                print(f"  - 선택된 방법: {data['method']}")
                
                # 품질 리포트
                quality = metadata.get('quality', {})
                if quality:
                    print_quality_report(quality)
                
                # 선택 이유
                merge_meta = metadata.get('merge_metadata', {})
                decision_reason = merge_meta.get('decision_reason', '')
                if decision_reason:
                    print(f"\n💡 선택 이유:")
                    print(f"  {decision_reason}")
            
            # Markdown 저장 경로
            markdown_path = data.get('markdown_path')
            if markdown_path:
                print(f"\n💾 Markdown 저장:")
                print(f"  {markdown_path}")
                
                # Markdown 미리보기
                md_text = data.get('markdown', '')
                if md_text:
                    preview_length = 500
                    preview = md_text[:preview_length]
                    print(f"\n📝 Markdown 미리보기 (처음 {preview_length}자):")
                    print("-" * 60)
                    print(preview)
                    if len(md_text) > preview_length:
                        print(f"... (총 {len(md_text)}자)")
                    print("-" * 60)
            
            print(f"\n✨ 테스트 완료!")
            
        else:
            print(f"\n❌ 처리 실패:")
            print(f"  - 오류: {result.get('error', 'Unknown error')}")
            print(f"  - 처리 시간: {result['processing_time_ms']}ms")
    
    except Exception as e:
        logger.exception(f"테스트 실패: {e}")
        print(f"\n❌ 테스트 실패: {e}")


def test_quality_validator():
    """품질 검증기 단독 테스트"""
    print_section("품질 검증기 테스트")
    
    from services.quality_validator import QualityValidator
    
    validator = QualityValidator()
    
    # 테스트 텍스트
    test_cases = [
        {
            "name": "고품질 텍스트",
            "text": """
# 보험 약관

## 제1장 총칙

### 제1조 (목적)
이 약관은 보험계약의 내용과 절차를 규정함을 목적으로 합니다.

### 제2조 (용어의 정의)
이 약관에서 사용하는 용어의 정의는 다음과 같습니다:
- 보험계약자: 보험회사와 계약을 체결하는 사람
- 피보험자: 보험 사고의 대상이 되는 사람

| 구분 | 내용 |
|------|------|
| 보험료 | 월 50,000원 |
| 보장 기간 | 10년 |
            """,
            "metadata": {"total_blocks": 5}
        },
        {
            "name": "저품질 텍스트",
            "text": "짧은 텍스트",
            "metadata": {}
        },
        {
            "name": "중복이 많은 텍스트",
            "text": "\n".join(["같은 줄"] * 20),
            "metadata": {}
        }
    ]
    
    for case in test_cases:
        print(f"\n\n테스트 케이스: {case['name']}")
        print("-" * 60)
        metrics = validator.validate(case['text'], case['metadata'])
        print_quality_report(metrics.__dict__)


def main():
    """메인 함수"""
    print("\n" + "="*60)
    print(" ISPL - 하이브리드 병합 테스트")
    print("="*60)
    
    print("\n테스트 모드 선택:")
    print("1. 하이브리드 병합 테스트 (PDF 필요)")
    print("2. 품질 검증기 단독 테스트")
    choice = input("선택 (1 또는 2): ").strip()
    
    if choice == "1":
        test_hybrid_merge()
    elif choice == "2":
        test_quality_validator()
    else:
        print("잘못된 선택입니다.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n테스트 중단됨")
    except Exception as e:
        logger.exception(f"예상치 못한 오류: {e}")

