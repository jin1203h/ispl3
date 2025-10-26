"""
하이브리드 병합 서비스
Path 1(PyMuPDF4LLM)과 Path 2(GPT-4 Vision)의 결과를 병합합니다.
"""
from difflib import SequenceMatcher
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from services.quality_validator import QualityValidator, QualityMetrics

logger = logging.getLogger(__name__)


@dataclass
class MergeResult:
    """병합 결과"""
    markdown: str                # 최종 Markdown 텍스트
    method: str                  # 선택된 방법 ("pymupdf", "vision", "hybrid")
    similarity: float            # 유사도 점수 (0.0 ~ 1.0)
    quality_metrics: QualityMetrics  # 품질 메트릭
    metadata: Dict[str, Any]     # 메타데이터


class HybridMerger:
    """하이브리드 병합기"""
    
    # 유사도 임계값
    HIGH_SIMILARITY_THRESHOLD = 0.8  # 높은 유사도 (Path 1 선택)
    
    def __init__(self):
        self.quality_validator = QualityValidator()
    
    def merge(
        self,
        pymupdf_result: Dict[str, Any],
        vision_result: Dict[str, Any]
    ) -> MergeResult:
        """
        PyMuPDF와 Vision 결과를 병합합니다.
        
        Args:
            pymupdf_result: PyMuPDF 추출 결과
            vision_result: GPT-4 Vision 추출 결과
        
        Returns:
            MergeResult 객체
        """
        logger.info("=== 하이브리드 병합 시작 ===")
        
        # 1. 유사도 계산
        similarity = self._calculate_similarity(
            pymupdf_result.get('markdown', ''),
            vision_result.get('markdown', '')
        )
        logger.info(f"유사도 점수: {similarity:.3f}")
        
        # 2. 최적 결과 선택
        selected_result, method = self._select_best_result(
            pymupdf_result,
            vision_result,
            similarity
        )
        logger.info(f"선택된 방법: {method}")
        
        # 3. 품질 검증
        markdown_text = selected_result.get('markdown', '')
        quality_metrics = self.quality_validator.validate(
            markdown_text,
            selected_result.get('metadata')
        )
        
        # 4. 메타데이터 생성
        metadata = self._create_metadata(
            pymupdf_result,
            vision_result,
            similarity,
            method
        )
        
        logger.info(
            f"병합 완료: method={method}, similarity={similarity:.3f}, "
            f"quality={quality_metrics.overall_score:.3f}, status={quality_metrics.status}"
        )
        
        return MergeResult(
            markdown=markdown_text,
            method=method,
            similarity=similarity,
            quality_metrics=quality_metrics,
            metadata=metadata
        )
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        두 텍스트의 유사도를 계산합니다 (SequenceMatcher 사용).
        
        Args:
            text1: 첫 번째 텍스트
            text2: 두 번째 텍스트
        
        Returns:
            유사도 점수 (0.0 ~ 1.0)
        """
        if not text1 or not text2:
            return 0.0
        
        # 공백 정규화 (비교 정확도 향상)
        text1_normalized = ' '.join(text1.split())
        text2_normalized = ' '.join(text2.split())
        
        # SequenceMatcher로 유사도 계산
        similarity = SequenceMatcher(
            None,
            text1_normalized,
            text2_normalized
        ).ratio()
        
        return similarity
    
    def _select_best_result(
        self,
        pymupdf_result: Dict[str, Any],
        vision_result: Dict[str, Any],
        similarity: float
    ) -> Tuple[Dict[str, Any], str]:
        """
        최적의 결과를 선택합니다.
        
        전략:
        - similarity > 0.8: PyMuPDF 결과 사용 (빠르고 정확함)
        - similarity <= 0.8: 품질 비교 후 선택
        
        Args:
            pymupdf_result: PyMuPDF 결과
            vision_result: Vision 결과
            similarity: 유사도 점수
        
        Returns:
            (선택된 결과, 방법명) 튜플
        """
        # 1. 높은 유사도 → PyMuPDF 선택 (더 빠르고 효율적)
        if similarity > self.HIGH_SIMILARITY_THRESHOLD:
            logger.info(
                f"유사도 {similarity:.3f} > {self.HIGH_SIMILARITY_THRESHOLD}: "
                "PyMuPDF 결과 선택 (빠른 처리)"
            )
            return pymupdf_result, "pymupdf"
        
        # 2. 낮은 유사도 → 품질 비교
        logger.info(
            f"유사도 {similarity:.3f} <= {self.HIGH_SIMILARITY_THRESHOLD}: "
            "품질 비교 수행"
        )
        
        pymupdf_text = pymupdf_result.get('markdown', '')
        vision_text = vision_result.get('markdown', '')
        
        pymupdf_quality = self.quality_validator.validate(
            pymupdf_text,
            pymupdf_result.get('metadata')
        )
        vision_quality = self.quality_validator.validate(
            vision_text,
            vision_result.get('metadata')
        )
        
        logger.info(
            f"품질 점수 - PyMuPDF: {pymupdf_quality.overall_score:.3f}, "
            f"Vision: {vision_quality.overall_score:.3f}"
        )
        
        # 품질이 더 높은 것 선택
        if pymupdf_quality.overall_score >= vision_quality.overall_score:
            return pymupdf_result, "pymupdf"
        else:
            return vision_result, "vision"
    
    def _create_metadata(
        self,
        pymupdf_result: Dict[str, Any],
        vision_result: Dict[str, Any],
        similarity: float,
        selected_method: str
    ) -> Dict[str, Any]:
        """
        병합 메타데이터를 생성합니다.
        
        Args:
            pymupdf_result: PyMuPDF 결과
            vision_result: Vision 결과
            similarity: 유사도 점수
            selected_method: 선택된 방법
        
        Returns:
            메타데이터 딕셔너리
        """
        pymupdf_meta = pymupdf_result.get('metadata', {})
        vision_meta = vision_result.get('metadata', {})
        
        return {
            "selected_method": selected_method,
            "similarity_score": similarity,
            "pymupdf_metadata": {
                "total_pages": pymupdf_meta.get('total_pages', 0),
                "processing_time": pymupdf_meta.get('processing_time', 0),
                "has_tables": pymupdf_meta.get('has_tables', False),
                "has_images": pymupdf_meta.get('has_images', False),
            },
            "vision_metadata": {
                "total_pages": vision_meta.get('total_pages', 0),
                "processing_time": vision_meta.get('processing_time', 0),
                "image_count": vision_meta.get('image_count', 0),
            },
            "decision_reason": self._get_decision_reason(similarity, selected_method)
        }
    
    def _get_decision_reason(self, similarity: float, method: str) -> str:
        """
        선택 이유를 설명합니다.
        
        Args:
            similarity: 유사도 점수
            method: 선택된 방법
        
        Returns:
            선택 이유 문자열
        """
        if similarity > self.HIGH_SIMILARITY_THRESHOLD:
            return (
                f"유사도 {similarity:.3f}로 두 방법의 결과가 매우 유사하여 "
                f"더 빠른 PyMuPDF 결과를 선택했습니다."
            )
        elif method == "pymupdf":
            return (
                f"유사도 {similarity:.3f}로 결과가 다르지만, "
                f"PyMuPDF의 품질 점수가 더 높아 선택했습니다."
            )
        else:
            return (
                f"유사도 {similarity:.3f}로 결과가 다르며, "
                f"GPT-4 Vision의 품질 점수가 더 높아 선택했습니다."
            )
    
    def merge_page_by_page(
        self,
        pymupdf_pages: List[Dict[str, Any]],
        vision_pages: List[Dict[str, Any]]
    ) -> List[MergeResult]:
        """
        페이지별로 병합을 수행합니다.
        
        Args:
            pymupdf_pages: PyMuPDF 페이지별 결과 리스트
            vision_pages: Vision 페이지별 결과 리스트
        
        Returns:
            페이지별 MergeResult 리스트
        """
        logger.info(f"페이지별 병합 시작: {len(pymupdf_pages)}페이지")
        
        results = []
        max_pages = max(len(pymupdf_pages), len(vision_pages))
        
        for i in range(max_pages):
            pymupdf_page = pymupdf_pages[i] if i < len(pymupdf_pages) else {}
            vision_page = vision_pages[i] if i < len(vision_pages) else {}
            
            if not pymupdf_page and not vision_page:
                continue
            
            # 페이지 누락 시 있는 쪽 사용
            if not pymupdf_page:
                logger.warning(f"페이지 {i+1}: PyMuPDF 결과 없음, Vision 결과 사용")
                result = self._create_single_method_result(vision_page, "vision")
            elif not vision_page:
                logger.warning(f"페이지 {i+1}: Vision 결과 없음, PyMuPDF 결과 사용")
                result = self._create_single_method_result(pymupdf_page, "pymupdf")
            else:
                result = self.merge(pymupdf_page, vision_page)
            
            results.append(result)
        
        logger.info(f"페이지별 병합 완료: {len(results)}페이지")
        return results
    
    def _create_single_method_result(
        self,
        result: Dict[str, Any],
        method: str
    ) -> MergeResult:
        """
        단일 방법 결과를 MergeResult로 변환합니다.
        
        Args:
            result: 추출 결과
            method: 방법명
        
        Returns:
            MergeResult 객체
        """
        markdown = result.get('markdown', '')
        quality_metrics = self.quality_validator.validate(
            markdown,
            result.get('metadata')
        )
        
        return MergeResult(
            markdown=markdown,
            method=method,
            similarity=1.0,  # 단일 방법이므로 1.0
            quality_metrics=quality_metrics,
            metadata={
                "selected_method": method,
                "single_method": True
            }
        )

