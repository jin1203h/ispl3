"""
답변 검증 서비스

AnswerAgent에서 생성된 답변의 신뢰도를 검증합니다.
할루시네이션 검증, 조항 번호 존재 확인, 컨텍스트 일치도 확인, 형식 검증을
수행하여 최종 신뢰도 점수를 산출합니다.
"""
import logging
import re
import time
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from models.answer_validation import AnswerValidation, ValidationDetail
from core.config import settings

logger = logging.getLogger(__name__)


class AnswerValidator:
    """답변 검증 서비스"""
    
    # 검증 가중치
    WEIGHTS = {
        "hallucination": 0.4,  # 할루시네이션 검증 40%
        "context": 0.3,        # 컨텍스트 일치 30%
        "clause": 0.2,         # 조항 존재 확인 20%
        "format": 0.1          # 형식 검증 10%
    }
    
    def __init__(self, openai_client=None):
        """
        AnswerValidator 초기화
        
        Args:
            openai_client: AsyncOpenAI 인스턴스 (의존성 주입)
        """
        # 의존성 주입: 외부에서 주입되지 않으면 기본 생성 (하위 호환성)
        if openai_client is None:
            from openai import AsyncOpenAI
            from core.config import settings
            openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            logger.warning("AnswerValidator: openai_client가 주입되지 않아 기본 인스턴스 생성")
        
        self.client = openai_client
        self.threshold = 0.7  # 신뢰도 임계값
        logger.info(f"AnswerValidator 초기화 완료 (threshold={self.threshold})")
    
    def _check_format(self, answer: str, search_results: list) -> ValidationDetail:
        """
        답변의 형식을 검증합니다.
        
        기존 AnswerAgent.validate_answer() 로직을 이동한 것입니다.
        구조화 여부, 참조 번호, 조항 번호 포함 여부를 확인합니다.
        
        Args:
            answer: 생성된 답변
            search_results: 검색 결과 리스트
        
        Returns:
            ValidationDetail 객체
        """
        checks = {
            "has_structure": False,
            "has_references": False,
            "has_clause_numbers": False
        }
        warnings = []
        
        # 1. 구조화 여부 확인 (별표 있거나 없어도 인정)
        has_answer_section = ("**📌 답변**" in answer or "📌 답변" in answer)
        has_reference_section = ("**📋 관련 약관**" in answer or "📋 관련 약관" in answer)
        
        if has_answer_section and has_reference_section:
            checks["has_structure"] = True
        else:
            warnings.append("구조화된 형식이 없습니다")
        
        # 2. 참조 번호 확인
        reference_pattern = r'\[참조\s*\d+\]'
        if re.search(reference_pattern, answer):
            checks["has_references"] = True
        else:
            warnings.append("참조 번호가 포함되지 않았습니다")
        
        # 3. 조항 번호 확인 (선택적)
        clause_pattern = r'제\s*\d+\s*조'
        if re.search(clause_pattern, answer):
            checks["has_clause_numbers"] = True
        
        # 4. 검색 결과에 조항 번호가 있는데 답변에 없는 경우 경고
        has_clause_in_results = any(
            result.get("clause_number") and result.get("clause_number") != "N/A"
            for result in search_results
        )
        if has_clause_in_results and not checks["has_clause_numbers"]:
            warnings.append(
                "검색 결과에 조항 번호가 있지만 답변에 포함되지 않았습니다"
            )
        
        # 점수 계산: 3가지 체크 중 통과한 개수 비율
        # has_clause_numbers는 선택적이므로 제외
        passed_count = sum([checks["has_structure"], checks["has_references"]])
        score = passed_count / 2  # 필수 2개
        
        # 모든 필수 항목 통과 여부
        passed = checks["has_structure"] and checks["has_references"]
        
        details = f"구조화: {checks['has_structure']}, 참조: {checks['has_references']}, 조항: {checks['has_clause_numbers']}"
        
        logger.debug(f"형식 검증: {details}")
        if warnings:
            logger.debug(f"형식 경고: {', '.join(warnings)}")
        
        return ValidationDetail(
            check_name="형식 검증",
            passed=passed,
            score=score,
            details=details
        )
    
    def _extract_clause_numbers(self, answer: str) -> List[str]:
        """
        답변에서 조항 번호를 추출합니다.
        
        Args:
            answer: 생성된 답변
        
        Returns:
            추출된 조항 번호 리스트 (예: ["제5조", "제15조"])
        """
        # 패턴: 제15조, 제 15 조, 제15조제2항 등
        pattern = r'제\s*(\d+)\s*조'
        matches = re.findall(pattern, answer)
        
        # 중복 제거 및 정규화
        clause_numbers = list(set(f"제{num}조" for num in matches))
        
        logger.debug(f"조항 번호 추출: {clause_numbers}")
        
        return clause_numbers
    
    def build_context_for_validation(self, search_results: list) -> str:
        """
        검증용 컨텍스트를 구성합니다.
        
        메타데이터를 제외하고 content만 포함하여 간결하게 만듭니다.
        
        Args:
            search_results: 검색 결과 리스트
        
        Returns:
            검증용 컨텍스트 문자열
        """
        if not search_results:
            return "검색 결과 없음"
        
        context_parts = []
        for idx, result in enumerate(search_results, 1):
            content = result.get("content", "")
            # 각 결과를 간단하게 표시
            context_parts.append(f"[{idx}] {content}")
        
        # 전체 컨텍스트 조립
        context = "\n\n".join(context_parts)
        
        # 1000자로 제한 (토큰 절약)
        if len(context) > 1000:
            context = context[:1000] + "..."
        
        return context
    
    async def _check_hallucination(
        self, 
        answer: str, 
        context: str
    ) -> ValidationDetail:
        """
        GPT-4o-mini를 사용하여 답변이 컨텍스트에 근거하는지 검증합니다.
        
        Args:
            answer: 생성된 답변
            context: 검증용 컨텍스트
        
        Returns:
            ValidationDetail 객체
        """
        try:
            logger.debug("할루시네이션 검증 시작 (GPT-4o-mini)")
            
            # GPT-4o-mini API 호출
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.0,
                max_tokens=200,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 답변 검증 전문가입니다. 답변이 제공된 컨텍스트에만 근거하는지 확인하세요."
                    },
                    {
                        "role": "user",
                        "content": f"""컨텍스트:
{context}

답변:
{answer}

이 답변이 컨텍스트에 근거합니까? JSON 형식으로만 답변하세요:
{{"grounded": true/false, "score": 0.0-1.0, "reason": "이유"}}"""
                    }
                ]
            )
            
            # JSON 응답 파싱
            import json
            response_text = response.choices[0].message.content.strip()
            
            # JSON 추출 (코드 블록 제거)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            
            grounded = result.get("grounded", False)
            score = float(result.get("score", 0.5))
            reason = result.get("reason", "")
            
            # 점수 범위 제한
            score = max(0.0, min(1.0, score))
            
            logger.debug(f"할루시네이션 검증 완료: grounded={grounded}, score={score}")
            
            return ValidationDetail(
                check_name="할루시네이션 검증",
                passed=grounded,
                score=score,
                details=reason[:200]  # 길이 제한
            )
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}, response: {response_text[:200]}")
            return ValidationDetail(
                check_name="할루시네이션 검증",
                passed=True,
                score=0.5,
                details=f"JSON 파싱 오류 (중립 점수)"
            )
        
        except Exception as e:
            logger.error(f"할루시네이션 검증 실패: {e}", exc_info=True)
            return ValidationDetail(
                check_name="할루시네이션 검증",
                passed=True,
                score=0.5,
                details=f"검증 오류: {str(e)[:100]}"
            )
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        텍스트에서 주요 키워드를 추출합니다.
        
        한글, 영문, 숫자 3글자 이상의 단어를 추출하고 중복을 제거합니다.
        
        Args:
            text: 키워드를 추출할 텍스트
        
        Returns:
            추출된 키워드 리스트
        """
        if not text:
            return []
        
        # 한글, 영문, 숫자 3글자 이상 추출
        keywords = re.findall(r'[가-힣a-zA-Z0-9]{3,}', text)
        
        # 중복 제거
        unique_keywords = list(set(keywords))
        
        logger.debug(f"키워드 추출: {len(unique_keywords)}개")
        
        return unique_keywords
    
    def _check_context_match(
        self, 
        answer: str, 
        search_results: list
    ) -> ValidationDetail:
        """
        답변의 주요 내용이 검색 결과에 포함되어 있는지 확인합니다.
        
        답변에서 키워드를 추출하고, 각 키워드가 검색 결과에 포함되는지
        확인하여 매칭률을 계산합니다.
        
        Args:
            answer: 생성된 답변
            search_results: 검색 결과 리스트
        
        Returns:
            ValidationDetail 객체
        """
        # 답변에서 키워드 추출
        keywords = self._extract_keywords(answer)
        
        # 키워드가 없으면 N/A (통과)
        if not keywords:
            logger.debug("키워드 없음 (N/A)")
            return ValidationDetail(
                check_name="컨텍스트 일치",
                passed=True,
                score=1.0,
                details="키워드 없음 (N/A)"
            )
        
        # 검색 결과가 없으면 매칭 불가
        if not search_results:
            logger.debug("검색 결과 없음")
            return ValidationDetail(
                check_name="컨텍스트 일치",
                passed=False,
                score=0.0,
                details="검색 결과 없음"
            )
        
        # 검색 결과의 모든 content 조합
        all_content = " ".join([r.get("content", "") for r in search_results])
        
        # 각 키워드가 검색 결과에 포함되는지 확인
        matched_keywords = [kw for kw in keywords if kw in all_content]
        match_count = len(matched_keywords)
        
        # 매칭률 계산
        score = match_count / len(keywords) if keywords else 1.0
        
        # 70% 이상 매칭되면 통과
        passed = score >= 0.7
        
        # 상세 설명
        details = f"{match_count}/{len(keywords)} 키워드 매칭 ({score*100:.1f}%)"
        
        logger.debug(f"컨텍스트 일치: {details}")
        
        return ValidationDetail(
            check_name="컨텍스트 일치",
            passed=passed,
            score=score,
            details=details
        )
    
    async def _check_clause_existence(
        self, 
        answer: str, 
        session: AsyncSession
    ) -> ValidationDetail:
        """
        답변에 언급된 조항 번호가 실제 DB에 존재하는지 확인합니다.
        
        Args:
            answer: 생성된 답변
            session: 데이터베이스 세션
        
        Returns:
            ValidationDetail 객체
        """
        clause_numbers = self._extract_clause_numbers(answer)
        
        # 조항 번호가 없으면 N/A (통과)
        if not clause_numbers:
            logger.debug("조항 번호 없음 (N/A)")
            return ValidationDetail(
                check_name="조항 존재 확인",
                passed=True,
                score=1.0,
                details="조항 번호 없음 (N/A)"
            )
        
        # session이 None이면 검증 불가
        if session is None:
            logger.warning("DB 세션이 없어 조항 존재 확인 불가")
            return ValidationDetail(
                check_name="조항 존재 확인",
                passed=True,
                score=0.5,
                details="DB 세션 없음 (검증 불가)"
            )
        
        try:
            # DB 쿼리: document_chunks 테이블에서 조항 번호 확인
            from sqlalchemy import text
            
            query = text("""
                SELECT DISTINCT clause_number 
                FROM document_chunks 
                WHERE clause_number = ANY(:clauses)
            """)
            
            result = await session.execute(query, {"clauses": clause_numbers})
            existing_clauses = {row[0] for row in result.fetchall()}
            
            # 존재하지 않는 조항 찾기
            missing_clauses = set(clause_numbers) - existing_clauses
            
            # 점수 계산: 존재하는 조항 비율
            if clause_numbers:
                score = len(existing_clauses) / len(clause_numbers)
            else:
                score = 1.0
            
            # 80% 이상 존재하면 통과
            passed = score >= 0.8
            
            # 상세 설명
            if missing_clauses:
                details = f"{len(existing_clauses)}/{len(clause_numbers)} 조항 존재, 미존재: {', '.join(sorted(missing_clauses))}"
            else:
                details = f"{len(existing_clauses)}/{len(clause_numbers)} 조항 모두 존재"
            
            logger.debug(f"조항 존재 확인: {details}")
            
            return ValidationDetail(
                check_name="조항 존재 확인",
                passed=passed,
                score=score,
                details=details
            )
        
        except Exception as e:
            logger.error(f"조항 존재 확인 중 오류: {e}", exc_info=True)
            return ValidationDetail(
                check_name="조항 존재 확인",
                passed=False,
                score=0.5,
                details=f"확인 오류: {str(e)}"
            )
    
    def _calculate_confidence(
        self,
        hallucination_check: ValidationDetail,
        clause_check: ValidationDetail,
        context_check: ValidationDetail,
        format_check: ValidationDetail
    ) -> float:
        """
        각 검증 항목의 점수를 가중 평균하여 최종 신뢰도 점수를 계산합니다.
        
        가중치:
        - hallucination: 40% (가장 중요)
        - context: 30%
        - clause: 20%
        - format: 10%
        
        Args:
            hallucination_check: 할루시네이션 검증 결과
            clause_check: 조항 존재 확인 결과
            context_check: 컨텍스트 일치 확인 결과
            format_check: 형식 검증 결과
        
        Returns:
            신뢰도 점수 (0.0 ~ 1.0)
        """
        confidence = (
            hallucination_check.score * self.WEIGHTS["hallucination"] +
            context_check.score * self.WEIGHTS["context"] +
            clause_check.score * self.WEIGHTS["clause"] +
            format_check.score * self.WEIGHTS["format"]
        )
        
        # 범위 제한 (0.0 ~ 1.0)
        confidence = max(0.0, min(1.0, confidence))
        
        logger.debug(
            f"신뢰도 계산: hallucination={hallucination_check.score:.2f}, "
            f"context={context_check.score:.2f}, "
            f"clause={clause_check.score:.2f}, "
            f"format={format_check.score:.2f} "
            f"→ confidence={confidence:.2f}"
        )
        
        return confidence
    
    async def validate(
        self,
        answer: str,
        search_results: list,
        session: AsyncSession
    ) -> AnswerValidation:
        """
        답변을 검증하고 신뢰도 점수를 계산합니다.
        
        4가지 검증 항목을 수행합니다:
        1. 형식 검증: 구조화, 참조 번호, 조항 번호 포함 여부
        2. 조항 존재 확인: 언급된 조항이 실제 DB에 존재하는지
        3. 할루시네이션 검증: GPT-4o-mini로 컨텍스트 근거 확인
        4. 컨텍스트 일치: 키워드 매칭률
        
        각 검증 결과를 가중 평균하여 최종 신뢰도 점수를 산출합니다.
        
        Args:
            answer: 생성된 답변
            search_results: 검색 결과 리스트
            session: 데이터베이스 세션
        
        Returns:
            AnswerValidation 객체
        """
        start_time = time.time()
        
        logger.info("답변 검증 시작")
        
        try:
            # 1. 동기 검증
            format_check = self._check_format(answer, search_results)
            context_check = self._check_context_match(answer, search_results)
            
            # 2. 비동기 검증 (순차 실행)
            # SQLAlchemy 비동기 세션의 안정성을 위해 순차 실행
            clause_check = await self._check_clause_existence(answer, session)
            
            context_text = self.build_context_for_validation(search_results)
            hallucination_check = await self._check_hallucination(answer, context_text)
            
            # 3. 신뢰도 점수 계산
            confidence_score = self._calculate_confidence(
                hallucination_check=hallucination_check,
                clause_check=clause_check,
                context_check=context_check,
                format_check=format_check
            )
            
            is_reliable = confidence_score >= self.threshold
            
            validation_time = time.time() - start_time
            
            logger.info(
                f"답변 검증 완료: confidence={confidence_score:.2f}, "
                f"reliable={is_reliable}, time={validation_time:.3f}s"
            )
            
            return AnswerValidation(
                confidence_score=confidence_score,
                is_reliable=is_reliable,
                hallucination_check=hallucination_check,
                clause_existence_check=clause_check,
                context_match_check=context_check,
                format_check=format_check,
                validation_time=validation_time,
                regeneration_count=0,
                warnings=[]
            )
        
        except Exception as e:
            logger.error(f"답변 검증 중 오류 발생: {e}", exc_info=True)
            
            # 오류 발생 시 기본값 반환
            validation_time = time.time() - start_time
            
            return AnswerValidation(
                confidence_score=0.5,
                is_reliable=False,
                hallucination_check=ValidationDetail(
                    check_name="할루시네이션 검증",
                    passed=False,
                    score=0.5,
                    details=f"검증 오류: {str(e)}"
                ),
                clause_existence_check=ValidationDetail(
                    check_name="조항 존재 확인",
                    passed=False,
                    score=0.5,
                    details=f"검증 오류: {str(e)}"
                ),
                context_match_check=ValidationDetail(
                    check_name="컨텍스트 일치",
                    passed=False,
                    score=0.5,
                    details=f"검증 오류: {str(e)}"
                ),
                format_check=ValidationDetail(
                    check_name="형식 검증",
                    passed=False,
                    score=0.5,
                    details=f"검증 오류: {str(e)}"
                ),
                validation_time=validation_time,
                regeneration_count=0,
                warnings=[f"검증 중 오류 발생: {str(e)}"]
            )

