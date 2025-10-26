"""
Answer Agent
검색 결과를 바탕으로 GPT-4를 사용하여 답변을 생성합니다.
"""
import logging
from openai import AsyncOpenAI

from agents.state import ISPLState
from core.config import settings
from core.database import AsyncSessionLocal
from services.answer_validator import AnswerValidator

logger = logging.getLogger(__name__)


class AnswerAgent:
    """검색 결과를 기반으로 답변을 생성하는 Agent"""
    
    MODEL = "gpt-4o"  # gpt-4o: 128K 토큰 컨텍스트 (이전: gpt-4 8K 토큰)
    TEMPERATURE = 0.1  # 정확한 답변을 위해 낮은 temperature
    MAX_TOKENS = 1000
    MAX_ATTEMPTS = 3  # 최초 1회 + 재생성 2회
    
    def __init__(self):
        """Answer Agent 초기화"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.validator = AnswerValidator()
        logger.info(
            f"AnswerAgent 초기화 완료: model={self.MODEL}, "
            f"temp={self.TEMPERATURE}, max_attempts={self.MAX_ATTEMPTS}"
        )
    
    def build_context(self, search_results: list) -> str:
        """
        검색 결과를 컨텍스트로 조립합니다.
        확장된 청크가 있는 경우 included_chunks 정보도 참조문서에 포함합니다.
        
        Args:
            search_results: 검색 결과 리스트
        
        Returns:
            조립된 컨텍스트 문자열
        """
        if not search_results:
            return "검색 결과가 없습니다."
        
        context_parts = []
        for idx, result in enumerate(search_results, 1):
            similarity = result.get("similarity", 0)
            content = result.get("content", "")
            document = result.get("document", {})
            filename = document.get("filename", "알 수 없음")
            page_number = result.get("page_number", "N/A")
            clause_number = result.get("clause_number", "N/A")
            
            # ⭐ 확장된 청크 정보 확인
            metadata = result.get("metadata", {})
            included_chunks = metadata.get("included_chunks", [])
            is_expanded = metadata.get("expanded", False)
            
            # 청크 ID 정보 구성
            chunk_id = result.get("chunk_id", "N/A")
            if is_expanded and included_chunks:
                # 확장된 경우: 포함된 모든 청크 ID 표시
                chunk_info = f"청크: {', '.join(map(str, included_chunks))}"
            else:
                # 일반 경우: 단일 청크 ID
                chunk_info = f"청크: {chunk_id}"
            
            context_parts.append(
                f"[참조 {idx}] (유사도: {similarity:.3f})\n"
                f"문서: {filename}, 페이지: {page_number}, 조항: {clause_number}\n"
                f"{chunk_info}\n"
                f"내용:\n{content}\n"
            )
        
        return "\n".join(context_parts)
    
    def build_system_prompt(self) -> str:
        """
        할루시네이션 방지가 강화된 시스템 프롬프트를 구성합니다.
        
        Returns:
            시스템 프롬프트
        """
        return """당신은 보험약관 전문 AI 어시스턴트입니다.

## 핵심 원칙 (반드시 준수)

### 1. 정확성 보장
- 제공된 참조 문서의 내용**만**을 사용하여 답변하세요
- 일반 상식이나 사전 학습 지식을 사용하지 마세요
- 참조 문서에 명시된 표현을 그대로 인용하세요

### 2. 출처 및 조항 번호 강제 인용
- 모든 주요 내용에 대해 **반드시** 참조 번호를 명시하세요 (예: [참조 1])
- 조항 번호가 있다면 **반드시** 포함하세요 (예: 제3조 제2항)
- 여러 참조를 조합할 경우 각각의 출처를 명시하세요

### 3. 한계 인정 및 투명성
- 참조 문서에 없는 내용은 "제공된 약관 문서에서는 해당 정보를 찾을 수 없습니다"라고 명확히 말하세요
- 불확실하거나 애매한 경우 "명확하지 않습니다" 또는 "추가 확인이 필요합니다"라고 답하세요
- **절대로** 추측하거나 일반적인 보험 상식으로 답변하지 마세요

### 4. 답변 구조 (필수)
**반드시 아래 형식을 정확히 따라주세요. 별표(**) 2개를 포함해야 합니다:**

**📌 답변**
(질문에 대한 핵심 답변. 조항 번호와 참조 번호 포함)

**📋 관련 약관**
- [참조 X] 조항명 및 번호: 주요 내용
- [참조 Y] 조항명 및 번호: 주요 내용

**⚠️ 주의사항**
(관련된 제한사항, 예외사항, 추가 확인 필요 사항 등. 없으면 생략)

**중요**: 각 섹션 제목은 반드시 별표 2개로 감싸야 합니다 (예: `**📌 답변**`)

## 할루시네이션 방지 체크리스트
답변하기 전 다음을 확인하세요:
- [ ] 모든 정보가 참조 문서에 있는가?
- [ ] 조항 번호를 명시했는가?
- [ ] 참조 번호를 인용했는가?
- [ ] 추측이나 일반화를 하지 않았는가?
- [ ] 구조화된 형식을 따랐는가?

## 예시

좋은 답변 ✅:
**📌 답변**
암 진단비는 최초 1회에 한하여 3,000만원이 지급됩니다 [참조 1, 제5조]. 단, 갑상선암 등 소액암은 300만원으로 제한됩니다 [참조 1, 제5조 제2항].

**📋 관련 약관**
- [참조 1] 제5조(암진단비의 지급): "피보험자가 암으로 진단 확정되었을 때 최초 1회에 한하여 3,000만원 지급"
- [참조 1] 제5조 제2항: "갑상선암, 기타피부암, 경계성종양, 제자리암은 300만원 지급"

나쁜 답변 ❌:
"일반적으로 암 진단비는 보험가입금액의 100%가 지급됩니다." (출처 없음, 일반화, 구조 미준수)

## 중요
참조 문서에 정보가 없거나 불확실하면, **"죄송하지만 제공된 약관 문서에서는 [질문 내용]에 대한 명확한 정보를 찾을 수 없습니다. 보험사에 직접 문의하시는 것을 권장드립니다."** 라고 답변하세요.
"""
    
    async def generate_answer(self, state: ISPLState) -> dict:
        """
        검색 결과를 바탕으로 답변을 생성합니다.
        신뢰도가 낮을 경우 최대 2회까지 재생성합니다.
        
        Args:
            state: 현재 상태
        
        Returns:
            업데이트할 상태 딕셔너리
        """
        query = state.get("query", "")
        search_results = state.get("search_results", [])
        error = state.get("error")
        
        # ⭐ 디버그: answer_agent가 받은 search_results 검증
        logger.info(f"⭐ answer_agent 받은 search_results 개수: {len(search_results)}")
        for idx, result in enumerate(search_results):
            metadata = result.get("metadata", {})
            is_expanded = metadata.get("expanded", False)
            included = metadata.get("included_chunks", [])
            logger.info(
                f"  결과[{idx}]: chunk_id={result.get('chunk_id')}, "
                f"expanded={is_expanded}, included_chunks={included}"
            )
        
        # 검색 단계에서 오류가 발생한 경우
        if error:
            logger.warning(f"검색 오류로 인한 답변 생성 실패: {error}")
            return {
                "final_answer": f"죄송합니다. {error}",
                "task_results": {
                    "answer": {
                        "success": False,
                        "error": error
                    }
                }
            }
        
        # 검색 결과가 없는 경우
        if not search_results:
            logger.info("검색 결과가 없어 기본 답변 반환")
            return {
                "final_answer": (
                    "죄송합니다. 질문하신 내용과 관련된 약관 정보를 찾을 수 없습니다.\n"
                    "다른 표현으로 다시 질문하시거나, 더 구체적인 키워드를 사용해주세요."
                ),
                "task_results": {
                    "answer": {
                        "success": True,
                        "no_results": True
                    }
                }
            }
        
        logger.info(f"답변 생성 시작: {len(search_results)}개 검색 결과 사용")
        
        # 컨텍스트 구성 (재생성 시에도 동일하게 사용)
        context = self.build_context(search_results)
        
        # 재생성 루프
        for attempt in range(self.MAX_ATTEMPTS):
            logger.info(f"답변 생성 시도 {attempt + 1}/{self.MAX_ATTEMPTS}")
            
            try:
                # GPT-4 API 호출
                response = await self.client.chat.completions.create(
                    model=self.MODEL,
                    temperature=self.TEMPERATURE,
                    max_tokens=self.MAX_TOKENS,
                    messages=[
                        {"role": "system", "content": self.build_system_prompt()},
                        {"role": "user", "content": f"참조 문서:\n\n{context}\n\n질문: {query}"}
                    ]
                )
                
                answer = response.choices[0].message.content
                tokens_used = response.usage.total_tokens
                
                logger.info(f"답변 생성됨: {len(answer)}자, {tokens_used}토큰")
                
                # AnswerValidator로 검증
                session = AsyncSessionLocal()
                try:
                    validation = await self.validator.validate(
                        answer=answer,
                        search_results=search_results,
                        session=session
                    )
                    # 재생성 횟수 기록
                    validation.regeneration_count = attempt
                finally:
                    await session.close()
                
                logger.info(
                    f"검증 완료: confidence={validation.confidence_score:.2f}, "
                    f"reliable={validation.is_reliable}"
                )
                
                # 신뢰도가 높거나 마지막 시도인 경우 반환
                if validation.is_reliable or attempt == self.MAX_ATTEMPTS - 1:
                    if validation.is_reliable:
                        logger.info(
                            f"✅ 답변 생성 성공: 신뢰도 {validation.confidence_score:.2f}, "
                            f"재생성 {attempt}회"
                        )
                    else:
                        logger.warning(
                            f"⚠️ 최종 답변 사용: 신뢰도 {validation.confidence_score:.2f}, "
                            f"재생성 {attempt}회 (최대 시도 도달)"
                        )
                    
                    return {
                        "final_answer": answer,
                        "task_results": {
                            "answer": {
                                "success": True,
                                "model": self.MODEL,
                                "tokens_used": tokens_used,
                                "validation": validation.dict()
                            }
                        }
                    }
                
                # 신뢰도가 낮으면 재생성
                logger.warning(
                    f"🔄 신뢰도 낮음 ({validation.confidence_score:.2f}), "
                    f"재생성 시도 {attempt + 1}/{self.MAX_ATTEMPTS - 1}"
                )
                
            except Exception as e:
                logger.error(f"답변 생성 시도 {attempt + 1} 중 오류 발생: {e}", exc_info=True)
                
                # 마지막 시도에서도 실패하면 오류 반환
                if attempt == self.MAX_ATTEMPTS - 1:
                    return {
                        "final_answer": f"죄송합니다. 답변 생성 중 오류가 발생했습니다: {str(e)}",
                        "task_results": {
                            "answer": {
                                "success": False,
                                "error": str(e),
                                "attempts": attempt + 1
                            }
                        }
                    }
                
                # 다음 시도 계속
                logger.info(f"다음 시도 진행 중... ({attempt + 2}/{self.MAX_ATTEMPTS})")
        
        # 이 코드는 도달하지 않아야 함 (안전장치)
        logger.error("예상치 못한 코드 경로 도달")
        return {
            "final_answer": "죄송합니다. 답변 생성 중 문제가 발생했습니다.",
            "task_results": {
                "answer": {
                    "success": False,
                    "error": "Unexpected code path"
                }
            }
        }


# 전역 Answer Agent 인스턴스
answer_agent = AnswerAgent()


async def answer_node(state: ISPLState) -> dict:
    """
    Answer Agent 노드 함수
    
    Args:
        state: 현재 상태
    
    Returns:
        업데이트할 상태 딕셔너리
    """
    return await answer_agent.generate_answer(state)

