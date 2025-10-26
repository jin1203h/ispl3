"""
Context Judgement Agent
컨텍스트의 충분성과 완결성을 판단하는 Agent입니다.
"""
import re
import logging
import tiktoken
from typing import List, Dict, Any, Optional

from agents.state import ISPLState
from services.chunk_expansion_service import ChunkExpansionService
from services.structure_analyzer import DocumentStructureAnalyzer  # ⭐ 추가
from services.service_container import get_openai_client
from core.database import AsyncSessionLocal
from services.vector_search import VectorSearchResult

logger = logging.getLogger(__name__)


class ContextJudgementAgent:
    """
    컨텍스트 판단 Agent
    
    검색된 청크의 충분성과 완결성을 판단하고,
    필요한 경우 청크 확장을 요청합니다.
    """
    
    # 최대 확장 시도 횟수 (무한 루프 방지)
    MAX_EXPANSION_COUNT = 3
    
    # LLM 모델
    MODEL = "gpt-4o"  # gpt-4o: 128K 토큰 컨텍스트 (이전: gpt-4 8K 토큰)
    TEMPERATURE = 0.1
    
    def __init__(self):
        """Context Judgement Agent 초기화"""
        self.chunk_expansion_service = ChunkExpansionService()
        self.structure_analyzer = DocumentStructureAnalyzer()
        self.client = get_openai_client()
        self.encoding = tiktoken.get_encoding("cl100k_base")
        logger.info(
            f"ContextJudgementAgent 초기화 완료: "
            f"max_expansion={self.MAX_EXPANSION_COUNT}"
        )
    
    def check_relevance_with_preprocessed(
        self,
        expanded_terms: List[str],
        content: str,
        min_relevance: float = 0.3
    ) -> bool:
        """
        전처리된 키워드로 질문과의 관련성을 판단합니다.
        
        Args:
            expanded_terms: query_preprocessor에서 전처리된 키워드 (조사 이미 제거됨)
            content: 청크 내용
            min_relevance: 최소 관련성 비율 (기본 0.3 = 30%)
        
        Returns:
            관련성 여부
        """
        if not expanded_terms:
            return True  # 키워드 없으면 관련있다고 판단
        
        content_lower = content.lower()
        matched = 0
        
        for term in expanded_terms:
            if term.lower() in content_lower:
                matched += 1
                logger.debug(f"키워드 매칭: '{term}' ✅")
            else:
                logger.debug(f"키워드 불일치: '{term}' ❌")
        
        relevance = matched / len(expanded_terms) if expanded_terms else 0
        is_relevant = relevance >= min_relevance
        
        logger.info(
            f"관련성 체크 (전처리된 키워드): {relevance:.2f} ({matched}/{len(expanded_terms)}), "
            f"relevant={is_relevant}, terms={expanded_terms}"
        )
        
        return is_relevant
    
    def check_relevance_by_similarity(
        self,
        result: Dict[str, Any],
        min_similarity: float = 0.5
    ) -> bool:
        """
        검색 유사도 점수로 관련성을 판단합니다.
        
        Args:
            result: 검색 결과 딕셔너리
            min_similarity: 최소 유사도 (기본 0.5)
        
        Returns:
            관련성 여부
        """
        similarity = result.get("similarity", 0)
        is_relevant = similarity >= min_similarity
        
        logger.debug(
            f"청크 {result.get('chunk_id')}: "
            f"similarity={similarity:.3f}, relevant={is_relevant}"
        )
        
        return is_relevant
    
    def should_expand_chunk(
        self,
        expanded_terms: List[str],
        result: Dict[str, Any],
        completeness: Dict[str, Any]
    ) -> bool:
        """
        청크 확장 필요 여부를 종합적으로 판단합니다.
        
        구조 분석 결과의 front_issues/back_issues를 활용하여
        관련없는 방향의 확장을 방지합니다.
        
        Args:
            expanded_terms: 전처리된 키워드 (동의어 포함)
            result: 검색 결과
            completeness: 완결성 정보 (front_issues, back_issues 포함)
        
        Returns:
            확장 필요 여부
        """
        chunk_id = result.get("chunk_id")
        
        # 1. 완결되면 확장 불필요
        if completeness["is_complete"]:
            return False
        
        # 2. 키워드 매칭 체크 (전처리된 키워드 사용)
        content = result.get("content", "")
        if not self.check_relevance_with_preprocessed(expanded_terms, content, min_relevance=0.3):
            logger.info(
                f"청크 {chunk_id}: 키워드 매칭 실패 → 확장 안함"
            )
            return False
        
        # 3. ⭐ 방향 조정 로직
        # 구조 분석에서 direction='both'로 판단된 경우,
        # 실제로 앞/뒤 어디에 문제가 있는지 세부적으로 확인하여
        # 불필요한 방향의 확장을 방지
        direction = completeness.get("direction")
        if direction == "both":
            front_issues = completeness.get("front_issues", [])
            back_issues = completeness.get("back_issues", [])
            
            # Case 1: 앞부분만 문제, 뒷부분은 괜찮음
            # 예: "9. 사전연명..." (무관, 불완전) + "... 제출한다." (관련, 완전)
            # → 앞부분만 확장 (prev)
            if front_issues and not back_issues:
                completeness["direction"] = "prev"
                logger.info(
                    f"청크 {chunk_id}: direction='both'였으나 "
                    f"앞부분만 문제 → prev로 조정"
                )
                logger.debug(f"  - front_issues: {front_issues}")
            
            # Case 2: 뒷부분만 문제, 앞부분은 괜찮음
            # 예: "제28조 신청은..." (관련, 완전) + "②항이 미" (관련, 불완전)
            # → 뒷부분만 확장 (next)
            elif back_issues and not front_issues:
                completeness["direction"] = "next"
                logger.info(
                    f"청크 {chunk_id}: direction='both'였으나 "
                    f"뒷부분만 문제 → next로 조정"
                )
                logger.debug(f"  - back_issues: {back_issues}")
            
            # Case 3: 앞뒤 모두 문제
            # 예: "9. 사전연명..." (무관, 불완전) + "②항이 미" (관련, 불완전)
            # → 키워드 매칭 통과했으므로 관련 내용은 청크 내 존재
            # → 보통 관련 내용은 뒷부분에 있고, 앞부분은 무관한 내용
            # → 뒷부분만 확장 (next)
            elif front_issues and back_issues:
                completeness["direction"] = "next"
                logger.info(
                    f"청크 {chunk_id}: 앞뒤 모두 불완전하지만 "
                    f"앞부분은 무관할 가능성 높음 → next로 조정"
                )
                logger.debug(f"  - front_issues: {front_issues}")
                logger.debug(f"  - back_issues: {back_issues}")
        
        # 관련성 있고 불완전함 → 확장 필요
        logger.info(
            f"청크 {chunk_id}: 불완전하고 관련있음 → 확장 "
            f"(direction={completeness.get('direction')})"
        )
        return True
    
    def check_sentence_completeness(
        self,
        content: str
    ) -> Dict[str, Any]:
        """
        문장 완결성을 규칙 기반으로 체크합니다.
        
        Args:
            content: 청크 내용
        
        Returns:
            {
                "is_complete": bool,
                "start_truncated": bool,
                "end_truncated": bool,
                "has_reference": bool,
                "confidence": float,
                "reasons": [이유 목록]
            }
        """
        if not content or not content.strip():
            return {
                "is_complete": False,
                "start_truncated": False,
                "end_truncated": False,
                "has_reference": False,
                "confidence": 0.0,
                "reasons": ["내용이 비어있음"]
            }
        
        content = content.strip()
        reasons = []
        start_truncated = False
        end_truncated = False
        has_reference = False
        
        # 1. 시작 부분 체크
        # 문장이 소문자나 조사로 시작하는 경우
        if re.match(r'^[a-z가-힣\s]{1,3}[은는이가을를]', content):
            start_truncated = True
            reasons.append("문장이 조사로 시작")
        
        # 접속사로 시작하는 경우
        connectives = ['그리고', '또한', '하지만', '그러나', '따라서', '그러므로', '이에']
        if any(content.startswith(word) for word in connectives):
            start_truncated = True
            reasons.append("접속사로 시작")
        
        # 2. 끝 부분 체크
        # 문장 종결 부호가 없는 경우
        if not re.search(r'[.!?。]$', content):
            end_truncated = True
            reasons.append("문장 종결 부호 없음")
        
        # 여는 괄호만 있고 닫는 괄호가 없는 경우
        open_parens = content.count('(') + content.count('[') + content.count('{')
        close_parens = content.count(')') + content.count(']') + content.count('}')
        if open_parens > close_parens:
            end_truncated = True
            reasons.append("괄호가 닫히지 않음")
        
        # 불완전한 인용부호
        if content.count('"') % 2 != 0 or content.count("'") % 2 != 0:
            end_truncated = True
            reasons.append("인용부호가 닫히지 않음")
        
        # 3. 참조 표현 체크
        reference_keywords = [
            '다음', '전항', '후술', '상기', '아래', '위의', '별표', 
            '제\d+조', '제\d+항', '참조', '기재된', '명시된'
        ]
        
        for keyword in reference_keywords:
            if re.search(keyword, content):
                has_reference = True
                reasons.append(f"참조 표현 발견: {keyword}")
                break
        
        # 4. 완결성 판단
        is_complete = not (start_truncated or end_truncated or has_reference)
        
        # 5. 신뢰도 계산
        confidence = 1.0
        if start_truncated:
            confidence -= 0.3
        if end_truncated:
            confidence -= 0.3
        if has_reference:
            confidence -= 0.2
        
        confidence = max(0.0, min(1.0, confidence))
        
        result = {
            "is_complete": is_complete,
            "start_truncated": start_truncated,
            "end_truncated": end_truncated,
            "has_reference": has_reference,
            "confidence": confidence,
            "reasons": reasons if reasons else ["문장이 완결됨"]
        }
        
        logger.debug(
            f"문장 완결성 체크: complete={is_complete}, "
            f"confidence={confidence:.2f}, reasons={reasons}"
        )
        
        return result
    
    async def llm_sufficiency_check(
        self,
        query: str,
        search_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        LLM을 활용하여 컨텍스트 충분성을 판단합니다.
        
        Args:
            query: 사용자 질의
            search_results: 검색 결과 목록
        
        Returns:
            {
                "is_sufficient": bool,
                "missing_info": str,
                "chunks_to_expand": [chunk_id들],
                "explanation": str
            }
        """
        try:
            # 컨텍스트 조립
            context_parts = []
            chunk_ids = []
            
            for idx, result in enumerate(search_results, 1):
                content = result.get("content", "")
                chunk_id = result.get("chunk_id")
                
                context_parts.append(f"[청크 {idx} (ID: {chunk_id})]:\n{content}")
                chunk_ids.append(chunk_id)
            
            context = "\n\n".join(context_parts)
            
            # LLM 프롬프트
            prompt = f"""다음 질문에 답변하기 위해 제공된 컨텍스트가 충분한지 판단해주세요.

질문: {query}

컨텍스트:
{context}

다음 형식으로 답변하세요:
1. 충분성: [충분함 | 불충분함]
2. 누락 정보: [무엇이 필요한지 구체적으로 설명, 충분하면 "없음"]
3. 확장 필요 청크 ID: [청크 ID들을 쉼표로 구분, 없으면 "없음"]
4. 설명: [판단 이유를 간단히]

중요: 청크의 내용이 잘려서 문맥이 불완전한 경우 "불충분함"으로 판단하세요."""
            
            # LLM 호출
            response = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 문서 컨텍스트의 충분성을 판단하는 전문가입니다."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.TEMPERATURE,
                max_tokens=500
            )
            
            llm_response = response.choices[0].message.content.strip()
            logger.info(f"LLM 충분성 판단 응답:\n{llm_response}")
            
            # 응답 파싱
            is_sufficient = "충분함" in llm_response and "불충분함" not in llm_response.split('\n')[0]
            
            # 누락 정보 추출
            missing_info = "없음"
            for line in llm_response.split('\n'):
                if '누락 정보' in line or 'missing' in line.lower():
                    missing_info = line.split(':', 1)[-1].strip()
                    break
            
            # 확장 필요 청크 ID 추출
            chunks_to_expand = []
            for line in llm_response.split('\n'):
                if '확장 필요' in line or 'chunk' in line.lower():
                    chunk_text = line.split(':', 1)[-1].strip()
                    if chunk_text != "없음":
                        # 숫자 추출
                        chunk_numbers = re.findall(r'\d+', chunk_text)
                        chunks_to_expand = [chunk_ids[int(num) - 1] for num in chunk_numbers if int(num) <= len(chunk_ids)]
                    break
            
            # 설명 추출
            explanation = llm_response
            for line in llm_response.split('\n'):
                if '설명' in line or 'explanation' in line.lower():
                    explanation = line.split(':', 1)[-1].strip()
                    break
            
            result = {
                "is_sufficient": is_sufficient,
                "missing_info": missing_info,
                "chunks_to_expand": chunks_to_expand,
                "explanation": explanation,
                "full_response": llm_response
            }
            
            logger.info(
                f"LLM 충분성 판단 완료: sufficient={is_sufficient}, "
                f"expand_count={len(chunks_to_expand)}"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"LLM 충분성 판단 중 오류: {e}", exc_info=True)
            # 오류 발생 시 보수적으로 충분하다고 판단 (기존 로직 유지)
            return {
                "is_sufficient": True,
                "missing_info": "판단 불가",
                "chunks_to_expand": [],
                "explanation": f"LLM 판단 오류: {str(e)}"
            }
    
    async def judge(self, state: ISPLState) -> dict:
        """
        컨텍스트 충분성을 종합적으로 판단합니다.
        
        Args:
            state: 현재 상태
        
        Returns:
            업데이트할 상태 딕셔너리
        """
        query = state.get("query", "")
        search_results = state.get("search_results", [])
        expansion_count = state.get("expansion_count", 0)
        
        # ⭐ 디버그: 받은 search_results 검증
        logger.info(f"⭐ context_judgement_agent 받은 search_results 개수: {len(search_results)}")
        for idx, result in enumerate(search_results):
            metadata = result.get("metadata", {})
            is_expanded = metadata.get("expanded", False)
            included = metadata.get("included_chunks", [])
            logger.info(
                f"  결과[{idx}]: chunk_id={result.get('chunk_id')}, "
                f"expanded={is_expanded}, included_chunks={included}"
            )
        
        # ⭐ 전처리 결과 가져오기
        task_results = state.get("task_results", {})
        preprocessing = task_results.get("search", {}).get("preprocessing", {})
        expanded_terms = preprocessing.get("expanded_terms", [])
        
        # 전처리 결과가 없으면 원본 쿼리에서 간단히 추출
        if not expanded_terms:
            # fallback: 간단한 단어 분리
            expanded_terms = [w for w in query.split() if len(w) >= 2]
            logger.warning(f"전처리 결과 없음, fallback 사용: {expanded_terms}")
        
        # 현재 토큰 수 계산
        current_tokens = sum(
            len(self.encoding.encode(r.get("content", "")))
            for r in search_results
        )
        
        logger.info(
            f"컨텍스트 판단 시작: query='{query[:50]}...', "
            f"results={len(search_results)}, "
            f"expansion_count={expansion_count}, "
            f"current_tokens={current_tokens}, "
            f"expanded_terms={len(expanded_terms)}개"
        )
        
        # 검색 결과가 없는 경우
        if not search_results:
            logger.warning("검색 결과가 없습니다.")
            return {
                "context_sufficient": True,  # 더 이상 확장 불가
                "chunks_to_expand": [],
                "task_results": {
                    "context_judgement": {
                        "success": True,
                        "sufficient": True,
                        "reason": "검색 결과 없음"
                    }
                },
                "next_agent": "answer_agent"
            }
        
        # 최대 확장 횟수 초과 확인
        if expansion_count >= self.MAX_EXPANSION_COUNT:
            logger.info(f"최대 확장 횟수 도달: {expansion_count}")
            return {
                "context_sufficient": True,  # 강제로 충분하다고 판단
                "chunks_to_expand": [],
                "task_results": {
                    "context_judgement": {
                        "success": True,
                        "sufficient": True,
                        "reason": "최대 확장 횟수 도달",
                        "expansion_count": expansion_count
                    }
                },
                "next_agent": "answer_agent"
            }
        
        # ⭐ 토큰 과다 체크 (2차 확장 시)
        # gpt-4o 변경으로 5500 → 10000 증가
        if expansion_count >= 1 and current_tokens > 10000:
            logger.warning(
                f"토큰 과다로 확장 중단: {current_tokens} 토큰"
            )
            return {
                "context_sufficient": True,  # 강제 종료
                "chunks_to_expand": [],
                "task_results": {
                    "context_judgement": {
                        "success": True,
                        "sufficient": True,
                        "reason": "토큰 제한 도달",
                        "current_tokens": current_tokens
                    }
                },
                "next_agent": "answer_agent"
            }
        
        # 1. 구조 기반 완결성 체크
        chunks_needing_expansion = []
        
        for result in search_results:
            content = result.get("content", "")
            chunk_id = result.get("chunk_id")
            
            # ⭐ 이미 확장된 청크는 재확장 제외
            metadata = result.get("metadata", {})
            if metadata.get("expanded", False):
                logger.info(
                    f"청크 {chunk_id}: 이미 확장됨 "
                    f"(included_chunks={metadata.get('included_chunks', [])}) → 스킵"
                )
                continue
            
            # ⭐ 구조 분석기를 사용한 완결성 체크
            completeness = self.structure_analyzer.check_completeness_with_structure(content)
            
            if not completeness["is_complete"]:
                # ⭐ 관련성 기반 확장 판단 (전처리된 키워드 사용)
                if self.should_expand_chunk(expanded_terms, result, completeness):
                    logger.info(
                        f"청크 {chunk_id} 불완전하고 관련있음: "
                        f"direction={completeness['direction']}, "
                        f"reasons={completeness['reasons']}"
                    )
                    chunks_needing_expansion.append({
                        "chunk_id": chunk_id,
                        "direction": completeness["direction"],
                        "reasons": completeness["reasons"]
                    })
                else:
                    logger.info(
                        f"청크 {chunk_id} 불완전하지만 질문과 무관: "
                        f"reasons={completeness['reasons']} → 확장 안함"
                    )
        
        # 2. LLM 기반 충분성 판단
        # ⭐ 2차 확장 시에는 LLM 판단만 사용
        if expansion_count >= 1:
            logger.info(f"2차 판단: LLM만 사용 (expansion_count={expansion_count})")
            llm_check = await self.llm_sufficiency_check(query, search_results)
            
            # LLM이 확장 필요하다고 판단한 청크 (최대 1개만)
            llm_expand_chunks = llm_check.get("chunks_to_expand", [])[:1]
            
            return {
                "search_results": search_results,  # ⭐ 확장된 결과를 answer_agent로 전달
                "context_sufficient": llm_check["is_sufficient"],
                "chunks_to_expand": [] if llm_check["is_sufficient"] else [
                    {"chunk_id": cid, "direction": "next"} for cid in llm_expand_chunks
                ],
                "task_results": {
                    "context_judgement": {
                        "success": True,
                        "sufficient": llm_check["is_sufficient"],
                        "llm_check": llm_check,
                        "expansion_count": expansion_count,
                        "current_tokens": current_tokens
                    }
                },
                "next_agent": "answer_agent" if llm_check["is_sufficient"] else "chunk_expansion_agent"
            }
        
        # 1차 판단: 구조 체크 + LLM 판단
        llm_check = await self.llm_sufficiency_check(query, search_results)
        
        # LLM이 추가로 확장이 필요하다고 판단한 청크 추가
        for chunk_id in llm_check["chunks_to_expand"]:
            # 이미 리스트에 있는지 확인
            if not any(c["chunk_id"] == chunk_id for c in chunks_needing_expansion):
                chunks_needing_expansion.append({
                    "chunk_id": chunk_id,
                    "direction": "both",  # LLM 판단은 양방향
                    "reasons": ["LLM 판단"]
                })
        
        # 3. 최종 판단
        is_sufficient = len(chunks_needing_expansion) == 0 and llm_check["is_sufficient"]
        
        logger.info(
            f"컨텍스트 판단 완료: sufficient={is_sufficient}, "
            f"expand_needed={len(chunks_needing_expansion)}"
        )
        
        # 4. 상태 업데이트
        if is_sufficient:
            # 충분한 경우 → Answer Agent로
            return {
                "context_sufficient": True,
                "chunks_to_expand": [],
                "task_results": {
                    "context_judgement": {
                        "success": True,
                        "sufficient": True,
                        "llm_check": llm_check,
                        "expansion_count": expansion_count
                    }
                },
                "next_agent": "answer_agent"
            }
        else:
            # 불충분한 경우 → Chunk Expansion Agent로
            return {
                "context_sufficient": False,
                "chunks_to_expand": chunks_needing_expansion,
                "task_results": {
                    "context_judgement": {
                        "success": True,
                        "sufficient": False,
                        "chunks_to_expand": chunks_needing_expansion,
                        "llm_check": llm_check,
                        "expansion_count": expansion_count
                    }
                },
                "next_agent": "chunk_expansion_agent"
            }


# 전역 Context Judgement Agent 인스턴스
context_judgement_agent = ContextJudgementAgent()


async def context_judgement_node(state: ISPLState) -> dict:
    """
    Context Judgement Agent 노드 함수
    
    Args:
        state: 현재 상태
    
    Returns:
        업데이트할 상태 딕셔너리
    """
    return await context_judgement_agent.judge(state)

