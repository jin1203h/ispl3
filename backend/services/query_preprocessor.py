"""
Query Preprocessor 서비스

사용자 질의를 전처리하여 검색 정확도를 향상시킵니다.
- 공백 정규화
- 전문용어 표준화
- 키워드 추출
- 조항 번호 추출
- 불완전 질의 감지
"""
import json
import re
import logging
from pathlib import Path
from typing import Optional, List, Tuple

from models.preprocessed_query import PreprocessedQuery
from utils.text_utils import extract_keywords

logger = logging.getLogger(__name__)


class QueryPreprocessor:
    """
    질의 전처리 서비스
    
    사용자의 자연어 질의를 정규화하고 표준화하여
    검색 정확도를 향상시킵니다.
    """
    
    def __init__(self):
        """QueryPreprocessor 초기화"""
        # 전문용어 사전 로딩
        self.term_dictionary = self._load_term_dictionary()
        self.synonym_dict = self.term_dictionary.get('synonyms', {})
        self.spacing_rules = self.term_dictionary.get('normalization', {}).get('spacing', {})
        self.incomplete_patterns = [
            (re.compile(p['pattern']), p['suggestion'])
            for p in self.term_dictionary.get('incomplete_patterns', [])
        ]
        
        logger.info(
            f"QueryPreprocessor 초기화 완료: "
            f"spacing_rules={len(self.spacing_rules)}개, "
            f"synonyms={len(self.synonym_dict)}개, "
            f"patterns={len(self.incomplete_patterns)}개"
        )
    
    def _load_term_dictionary(self) -> dict:
        """
        보험 전문용어 사전을 로딩합니다.
        
        Returns:
            전문용어 사전 딕셔너리
        
        Raises:
            FileNotFoundError: 사전 파일이 없는 경우
            json.JSONDecodeError: JSON 형식이 잘못된 경우
        """
        json_path = Path(__file__).parent.parent / 'data' / 'insurance_terms.json'
        
        logger.debug(f"전문용어 사전 로딩 중: {json_path}")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"전문용어 사전 로딩 완료: {json_path}")
            return data
        
        except FileNotFoundError:
            logger.error(f"전문용어 사전 파일을 찾을 수 없습니다: {json_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"전문용어 사전 JSON 형식 오류: {e}")
            raise
    
    def _normalize(self, query: str) -> str:
        """
        질의를 정규화합니다.
        - 여러 공백을 하나로 통합
        - 앞뒤 공백 제거
        
        Args:
            query: 원본 질의
        
        Returns:
            정규화된 질의
        """
        # 여러 공백을 하나로
        normalized = re.sub(r'\s+', ' ', query)
        # 앞뒤 공백 제거
        normalized = normalized.strip()
        
        logger.debug(f"정규화: '{query}' → '{normalized}'")
        
        return normalized
    
    def _standardize_terms(self, query: str) -> str:
        """
        전문용어를 표준화합니다.
        spacing_rules를 적용하여 공백을 추가합니다.
        
        Args:
            query: 정규화된 질의
        
        Returns:
            표준화된 질의
        
        Example:
            "암진단비" → "암 진단비"
            "보험금액" → "보험 금액"
        """
        standardized = query
        
        # spacing_rules 적용
        for term, replacement in self.spacing_rules.items():
            if term in standardized:
                standardized = standardized.replace(term, replacement)
                logger.debug(f"표준화: '{term}' → '{replacement}'")
        
        if standardized != query:
            logger.info(f"전문용어 표준화: '{query}' → '{standardized}'")
        
        return standardized
    
    def _extract_clause_number(self, query: str) -> Optional[str]:
        """
        쿼리에서 조항 번호를 추출합니다.
        
        SearchAgent의 extract_clause_number() 로직을 이동한 것입니다.
        
        Args:
            query: 사용자 질의
        
        Returns:
            추출된 조항 번호 (예: "제15조") 또는 None
        
        Example:
            "제15조의 내용" → "제15조"
            "15조 보장 내용" → "제15조"
            "보험금 얼마" → None
        """
        # 패턴: "제 N조", "제N조", "N조"
        patterns = [
            r'제\s*(\d+)\s*조',  # 제15조, 제 15 조
            r'(\d+)\s*조',       # 15조
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                clause_num = match.group(1)
                clause_str = f"제{clause_num}조"
                logger.info(f"조항 번호 추출: {clause_str}")
                return clause_str
        
        return None
    
    def _expand_synonyms(self, query: str) -> List[str]:
        """
        동의어를 확장하여 여러 검색 쿼리를 생성합니다.
        
        Args:
            query: 표준화된 질의
        
        Returns:
            확장된 쿼리 리스트 (원본 포함)
        
        Example:
            "암 진단비 얼마" → ["암 진단비 얼마", "악성신생물 진단비 얼마", "암질환 진단비 얼마"]
        """
        expanded = [query]  # 원본 포함
        
        # 각 동의어 확장
        for term, synonyms in self.synonym_dict.items():
            if term in query:
                # 동의어로 대체한 쿼리 생성
                for synonym in synonyms:
                    expanded_query = query.replace(term, synonym)
                    if expanded_query not in expanded:
                        expanded.append(expanded_query)
        
        if len(expanded) > 1:
            logger.info(f"동의어 확장: {len(expanded)}개 쿼리 생성")
            logger.debug(f"확장된 쿼리: {expanded}")
        
        return expanded
    
    def _check_completeness(self, query: str) -> Tuple[bool, List[str]]:
        """
        질의의 완전성을 검사합니다.
        
        불완전 질의 패턴에 매칭되면 사용자에게 제안사항을 제공합니다.
        
        Args:
            query: 표준화된 질의
        
        Returns:
            (is_complete, suggestions) 튜플
            - is_complete: 질의가 완전하면 True, 불완전하면 False
            - suggestions: 불완전 질의 시 제안사항 리스트
        
        Example:
            "얼마" → (False, ["구체적인 항목을 추가해주세요..."])
            "암 진단비 얼마인가요?" → (True, [])
        """
        suggestions = []
        
        # 불완전 질의 패턴 매칭
        for pattern, suggestion in self.incomplete_patterns:
            if pattern.search(query):
                suggestions.append(suggestion)
        
        is_complete = len(suggestions) == 0
        
        if not is_complete:
            logger.info(f"불완전 질의 감지: '{query[:50]}...'")
            logger.debug(f"제안사항: {suggestions}")
        
        return is_complete, suggestions
    
    async def preprocess(self, query: str) -> PreprocessedQuery:
        """
        질의 전처리 파이프라인을 실행합니다.
        
        1. 정규화 (공백)
        2. 전문용어 표준화
        3. 키워드 추출 (조사 제거 + 동의어 확장)
        4. 조항 번호 추출
        5. 불완전 질의 감지
        
        Args:
            query: 원본 사용자 질의
        
        Returns:
            PreprocessedQuery 객체
        """
        try:
            logger.debug(f"질의 전처리 시작: '{query}'")
            
            # 1. 정규화 (공백)
            normalized = self._normalize(query)
            
            # 2. 전문용어 표준화
            standardized = self._standardize_terms(normalized)
            
            # 3. 키워드 추출 (조사 제거) - 공통 유틸리티 사용
            base_keywords = extract_keywords(standardized)
            
            # 4. 동의어 키워드 확장
            expanded_keywords = set(base_keywords)  # 중복 제거용
            for keyword in base_keywords:
                # 동의어 사전에서 찾기
                for term, synonyms in self.synonym_dict.items():
                    if term in keyword or keyword in term:
                        # 동의어도 키워드로 추가
                        for synonym in synonyms:
                            synonym_keywords = extract_keywords(synonym)
                            expanded_keywords.update(synonym_keywords)
                        # 원래 용어도 포함
                        term_keywords = extract_keywords(term)
                        expanded_keywords.update(term_keywords)
            
            expanded_terms = list(expanded_keywords)
            
            # 5. 조항 번호 추출
            clause_number = self._extract_clause_number(standardized)
            
            # 6. 불완전 질의 감지
            is_complete, suggestions = self._check_completeness(standardized)
            
            # PreprocessedQuery 생성
            result = PreprocessedQuery(
                original=query,
                normalized=normalized,
                standardized=standardized,
                expanded_terms=expanded_terms,  # 동의어 포함 키워드 리스트
                clause_number=clause_number,
                is_complete=is_complete,
                suggestions=suggestions
            )
            
            logger.info(
                f"질의 전처리 완료: standardized='{standardized}', "
                f"base_keywords={base_keywords}, "
                f"expanded_keywords={expanded_terms}, "
                f"clause={clause_number}"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"질의 전처리 중 오류 발생: {e}", exc_info=True)
            
            # fallback: 원본 쿼리 반환
            logger.warning("전처리 실패, 원본 쿼리로 fallback")
            return PreprocessedQuery(
                original=query,
                normalized=query,
                standardized=query,
                expanded_terms=[query],
                clause_number=None,
                is_complete=True,  # 전처리 실패 시 검색 진행
                suggestions=[]
            )

