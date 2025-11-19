"""
텍스트 처리 유틸리티
키워드 추출, 조사 제거 등 텍스트 전처리 관련 공통 함수를 제공합니다.
"""
import logging
from typing import List

logger = logging.getLogger(__name__)

# Kiwi 형태소 분석기 전역 인스턴스 (성능 최적화)
_kiwi_instance = None


def _get_kiwi():
    """
    Kiwi 형태소 분석기 인스턴스를 반환합니다.
    
    싱글톤 패턴으로 한 번만 초기화하여 성능을 최적화합니다.
    """
    global _kiwi_instance
    
    if _kiwi_instance is None:
        try:
            from kiwipiepy import Kiwi
            _kiwi_instance = Kiwi()
            logger.info("Kiwi 형태소 분석기 초기화 완료")
        except ImportError:
            logger.error(
                "kiwipiepy가 설치되지 않았습니다. "
                "pip install kiwipiepy 를 실행하세요."
            )
            raise
        except Exception as e:
            logger.error(f"Kiwi 초기화 중 오류: {e}", exc_info=True)
            raise
    
    return _kiwi_instance


def extract_keywords(query: str) -> List[str]:
    """
    질의에서 키워드를 추출합니다.
    
    Kiwi 형태소 분석기를 사용하여 명사만 추출합니다.
    인접한 명사를 결합하여 복합명사를 유지합니다.
    
    Args:
        query: 검색 질의 문자열
    
    Returns:
        키워드 리스트 (명사만)
    
    Example:
        >>> extract_keywords("면책기간은 얼마나 되나요?")
        ["면책기간"]
        
        >>> extract_keywords("경계성종양이란?")
        ["경계성종양"]
        
        >>> extract_keywords("암 진단금은?")
        ["암", "진단금"]
    """
    if not query or not query.strip():
        return []
    
    # 중요한 1글자 명사 목록 (보험/의료 관련)
    IMPORTANT_SINGLE_CHAR = {
        '암', '간', '폐', '위', '뇌', '심', '장', '혈', '골', '신',
        '눈', '귀', '코', '입', '치', '손', '발', '다리', '팔', '목'
    }
    
    # 의문사 제외 목록 (검색 쿼리에 불필요한 단어)
    QUESTION_WORDS = {
        '얼마', '어디', '언제', '누구', '무엇', '뭐', '왜', '어떻게',
        '어느', '어떤', '무슨', '몇', '어찌', '하는', '되는', '있는',
        '것', '수', '때', '등', '및', '또'  # 의존명사도 제외
    }
    
    try:
        # Kiwi 형태소 분석기 사용
        kiwi = _get_kiwi()
        tokens = kiwi.tokenize(query)
        
        # 명사 토큰 추출 및 복합명사 결합
        # NNG: 일반명사 (예: 보험, 진단, 치료)
        # NNP: 고유명사 (예: 흥국생명, 서울)
        # NNB: 의존명사 (예: 것, 수, 때)
        # XSN: 명사 파생 접미사 (예: 성)
        
        keywords = []
        current_noun = []
        prev_end = -1
        
        for token in tokens:
            # 명사 관련 태그 체크
            is_noun = token.tag in ['NNG', 'NNP', 'NNB', 'XSN']
            
            if is_noun:
                # 이전 명사와 연속되어 있으면 결합
                if current_noun and token.start == prev_end:
                    current_noun.append(token.form)
                else:
                    # 이전 복합명사 저장
                    if current_noun:
                        compound = ''.join(current_noun)
                        # 2글자 이상 또는 중요한 1글자 명사, 단 의문사는 제외
                        if (len(compound) >= 2 or compound in IMPORTANT_SINGLE_CHAR) and compound not in QUESTION_WORDS:
                            keywords.append(compound)
                    # 새로운 복합명사 시작
                    current_noun = [token.form]
                
                prev_end = token.start + token.len
            else:
                # 명사가 아니면 이전까지의 복합명사 저장
                if current_noun:
                    compound = ''.join(current_noun)
                    # 2글자 이상 또는 중요한 1글자 명사, 단 의문사는 제외
                    if (len(compound) >= 2 or compound in IMPORTANT_SINGLE_CHAR) and compound not in QUESTION_WORDS:
                        keywords.append(compound)
                    current_noun = []
                    prev_end = -1
        
        # 마지막 복합명사 처리
        if current_noun:
            compound = ''.join(current_noun)
            # 2글자 이상 또는 중요한 1글자 명사, 단 의문사는 제외
            if (len(compound) >= 2 or compound in IMPORTANT_SINGLE_CHAR) and compound not in QUESTION_WORDS:
                keywords.append(compound)
        
        # 중복 제거 (순서 유지)
        unique_keywords = list(dict.fromkeys(keywords))
        
        if not unique_keywords:
            # 명사가 없으면 원본 쿼리를 단순 분리 (fallback)
            logger.warning(f"명사 추출 실패, fallback 사용: '{query}'")
            import re
            clean_query = re.sub(r'[^\w\s가-힣]', ' ', query)
            words = [w for w in clean_query.split() if len(w) >= 2]
            unique_keywords = list(dict.fromkeys(words))  # 중복 제거
        
        logger.debug(f"키워드 추출: '{query}' → {unique_keywords}")
        
        return unique_keywords
    
    except Exception as e:
        logger.error(f"키워드 추출 중 오류: {e}, fallback 사용", exc_info=True)
        
        # 오류 시 기존 방식 fallback
        return _extract_keywords_fallback(query)


def _extract_keywords_fallback(query: str) -> List[str]:
    """
    형태소 분석기 오류 시 사용하는 fallback 함수
    
    기존 규칙 기반 방식을 사용합니다.
    """
    import re
    
    # 특수문자 제거
    clean_query = re.sub(r'[^\w\s가-힣]', ' ', query)
    
    # 단어 분리
    words = clean_query.split()
    if not words:
        return []
    
    # 간단한 조사 제거 (최소한만)
    korean_particles = [
        '은', '는', '이', '가', '을', '를', '의', '에', '에서', 
        '으로', '로', '와', '과', '도', '만', '이란', '란'
    ]
    
    # 의문사 제거
    question_words = [
        '어떻게', '어디', '언제', '누구', '무엇', '왜', 
        '어느', '얼마', '어떤', '무슨', '얼마나'
    ]
    
    exclude_words = set(korean_particles + question_words)
    
    filtered_words = []
    for word in words:
        if len(word) >= 2 and word not in exclude_words:
            # 단어 끝의 조사 제거
            clean_word = word
            for particle in korean_particles:
                if clean_word.endswith(particle) and len(clean_word) > len(particle):
                    clean_word = clean_word[:-len(particle)]
                    break
            
            if len(clean_word) >= 2:
                filtered_words.append(clean_word)
    
    if not filtered_words:
        filtered_words = [w for w in words if len(w) >= 2]
    
    # 중복 제거
    return list(dict.fromkeys(filtered_words))


# ═══════════════════════════════════════════════════════════════
# 참고: 기존 하드코딩 방식 (보존용, 사용 안함)
# ═══════════════════════════════════════════════════════════════
"""
기존 extract_keywords() 함수 - 규칙 기반 방식

문제점:
1. 조사/의문사 리스트 불완전 (매번 추가 필요)
2. 품사 구분 불가 (명사, 동사, 형용사 섞임)
3. 복합어 분해 불가 ("갑상선암진단비" → 하나로 인식)
4. 활용형 통일 불가 ("입원했을", "입원하는" → 다르게 인식)
5. 띄어쓰기 민감 ("경계성종양" vs "경계성 종양")

개선:
- Kiwi 형태소 분석기 사용으로 모든 문제 해결
- 하드코딩된 리스트 불필요
- 자동으로 품사 구분 및 기본형 추출
"""

