"""
품질 검증 서비스
PDF 추출 결과의 품질을 평가합니다.
"""
import re
from typing import Dict, List, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class QualityMetrics:
    """품질 평가 메트릭"""
    completeness: float  # 완전성 (0.0 ~ 1.0)
    consistency: float   # 일관성 (0.0 ~ 1.0)
    accuracy: float      # 정확도 추정 (0.0 ~ 1.0)
    overall_score: float # 종합 점수 (0.0 ~ 1.0)
    issues: List[str]    # 발견된 문제점
    status: str          # "excellent", "good", "acceptable", "poor"


class QualityValidator:
    """품질 검증기"""
    
    # 품질 상태 임계값
    EXCELLENT_THRESHOLD = 0.9
    GOOD_THRESHOLD = 0.75
    ACCEPTABLE_THRESHOLD = 0.6
    
    def validate(
        self,
        markdown_text: str,
        metadata: Dict[str, Any] = None
    ) -> QualityMetrics:
        """
        Markdown 텍스트의 품질을 검증합니다.
        
        Args:
            markdown_text: 검증할 Markdown 텍스트
            metadata: 추가 메타데이터 (페이지 수, 블록 수 등)
        
        Returns:
            QualityMetrics 객체
        """
        issues = []
        
        # 1. 완전성 검사
        completeness = self._check_completeness(markdown_text, metadata)
        if completeness < 0.5:
            issues.append("콘텐츠가 불완전할 수 있습니다")
        
        # 2. 일관성 검사
        consistency = self._check_consistency(markdown_text)
        if consistency < 0.7:
            issues.append("중복 또는 일관성 문제가 발견되었습니다")
        
        # 3. 정확도 추정
        accuracy = self._estimate_accuracy(markdown_text, metadata)
        if accuracy < 0.6:
            issues.append("추출 정확도가 낮을 수 있습니다")
        
        # 종합 점수 계산 (가중 평균)
        overall_score = (
            completeness * 0.4 +
            consistency * 0.3 +
            accuracy * 0.3
        )
        
        # 상태 결정
        if overall_score >= self.EXCELLENT_THRESHOLD:
            status = "excellent"
        elif overall_score >= self.GOOD_THRESHOLD:
            status = "good"
        elif overall_score >= self.ACCEPTABLE_THRESHOLD:
            status = "acceptable"
        else:
            status = "poor"
            issues.append("전반적인 품질이 낮습니다. 수동 검토가 필요할 수 있습니다")
        
        logger.info(
            f"품질 검증 완료: 완전성={completeness:.2f}, "
            f"일관성={consistency:.2f}, 정확도={accuracy:.2f}, "
            f"종합={overall_score:.2f}, 상태={status}"
        )
        
        return QualityMetrics(
            completeness=completeness,
            consistency=consistency,
            accuracy=accuracy,
            overall_score=overall_score,
            issues=issues,
            status=status
        )
    
    def _check_completeness(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> float:
        """
        완전성 검사: 콘텐츠가 충분히 추출되었는지 확인
        
        Args:
            text: Markdown 텍스트
            metadata: 메타데이터
        
        Returns:
            완전성 점수 (0.0 ~ 1.0)
        """
        if not text or len(text.strip()) == 0:
            return 0.0
        
        # 기본 지표
        text_length = len(text)
        word_count = len(text.split())
        line_count = len(text.split('\n'))
        
        # 점수 계산 (휴리스틱)
        score = 0.0
        
        # 1. 텍스트 길이 (최소 100자)
        if text_length >= 100:
            score += 0.3
        else:
            score += (text_length / 100) * 0.3
        
        # 2. 단어 수 (최소 20단어)
        if word_count >= 20:
            score += 0.3
        else:
            score += (word_count / 20) * 0.3
        
        # 3. 줄 수 (최소 5줄)
        if line_count >= 5:
            score += 0.2
        else:
            score += (line_count / 5) * 0.2
        
        # 4. 메타데이터 기반 검증 (선택적)
        if metadata:
            expected_blocks = metadata.get('total_blocks', 0)
            actual_blocks = len(re.findall(r'\n\n+', text))  # 단락 수 추정
            
            if expected_blocks > 0:
                block_ratio = min(actual_blocks / expected_blocks, 1.0)
                score += block_ratio * 0.2
            else:
                score += 0.2  # 메타데이터 없으면 기본 점수
        else:
            score += 0.2
        
        return min(score, 1.0)
    
    def _check_consistency(self, text: str) -> float:
        """
        일관성 검사: 중복 또는 불일치 확인
        
        Args:
            text: Markdown 텍스트
        
        Returns:
            일관성 점수 (0.0 ~ 1.0)
        """
        if not text:
            return 0.0
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if len(lines) == 0:
            return 0.0
        
        # 1. 중복 라인 비율
        unique_lines = set(lines)
        duplicate_ratio = 1.0 - (len(unique_lines) / len(lines))
        
        # 2. 과도한 중복 감지 (연속된 동일 라인)
        consecutive_duplicates = 0
        for i in range(1, len(lines)):
            if lines[i] == lines[i-1]:
                consecutive_duplicates += 1
        
        consecutive_duplicate_ratio = consecutive_duplicates / len(lines) if len(lines) > 0 else 0
        
        # 점수 계산 (중복이 적을수록 높은 점수)
        score = 1.0 - (duplicate_ratio * 0.5 + consecutive_duplicate_ratio * 0.5)
        
        return max(score, 0.0)
    
    def _estimate_accuracy(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> float:
        """
        정확도 추정: 추출 품질 간접 평가
        
        Args:
            text: Markdown 텍스트
            metadata: 메타데이터 (신뢰도 정보 등)
        
        Returns:
            정확도 점수 (0.0 ~ 1.0)
        """
        if not text:
            return 0.0
        
        score = 0.0
        
        # 1. Markdown 구조 품질 (헤더, 리스트, 표 등)
        has_headers = bool(re.search(r'^#+\s+\w+', text, re.MULTILINE))
        has_lists = bool(re.search(r'^\s*[-*]\s+\w+', text, re.MULTILINE))
        has_tables = bool(re.search(r'\|.*\|', text))
        
        structure_score = (
            (0.4 if has_headers else 0) +
            (0.3 if has_lists else 0) +
            (0.3 if has_tables else 0)
        )
        score += structure_score * 0.4
        
        # 2. 한글/영문 비율 (보험약관은 주로 한글)
        korean_chars = len(re.findall(r'[가-힣]', text))
        total_chars = len(re.sub(r'\s', '', text))
        
        if total_chars > 0:
            korean_ratio = korean_chars / total_chars
            # 한글 비율이 30% 이상이면 양호
            if korean_ratio >= 0.3:
                score += 0.3
            else:
                score += korean_ratio * 0.3
        
        # 3. 메타데이터 기반 신뢰도 (선택적)
        if metadata and 'confidence' in metadata:
            confidence = metadata['confidence']
            score += confidence * 0.3
        else:
            score += 0.3  # 메타데이터 없으면 기본 점수
        
        return min(score, 1.0)
    
    def compare_results(
        self,
        result1: Dict[str, Any],
        result2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        두 추출 결과를 비교하여 품질이 더 높은 것을 선택합니다.
        
        Args:
            result1: 첫 번째 결과 (예: PyMuPDF)
            result2: 두 번째 결과 (예: Vision)
        
        Returns:
            비교 결과 및 추천
        """
        text1 = result1.get('markdown', '')
        text2 = result2.get('markdown', '')
        
        quality1 = self.validate(text1, result1.get('metadata'))
        quality2 = self.validate(text2, result2.get('metadata'))
        
        recommendation = "result1" if quality1.overall_score >= quality2.overall_score else "result2"
        
        return {
            "result1_quality": quality1.__dict__,
            "result2_quality": quality2.__dict__,
            "recommendation": recommendation,
            "score_difference": abs(quality1.overall_score - quality2.overall_score)
        }

