"""
할루시네이션 방지 프롬프트 테스트
답변의 구조화, 참조 인용, 조항 번호 포함 여부를 검증합니다.
"""
import sys
import os
from pathlib import Path

# 테스트 환경 설정
os.environ["TESTING"] = "true"

# backend 디렉토리를 Python 경로에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import asyncio
import logging

from agents.graph import run_graph

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_hallucination_prevention():
    """할루시네이션 방지 프롬프트 테스트"""
    logger.info("=" * 80)
    logger.info("할루시네이션 방지 프롬프트 테스트")
    logger.info("=" * 80)
    
    # 테스트 케이스들
    test_cases = [
        {
            "name": "정상 질의 - 약관 내용 존재",
            "query": "암 진단비는 얼마인가요?",
            "expected_validation": {
                "has_structure": True,
                "has_references": True,
                "has_clause_numbers": True  # 조항이 있으면 True
            }
        },
        {
            "name": "애매한 질의 - 한계 인정 테스트",
            "query": "이 보험의 장단점은 무엇인가요?",
            "expected_validation": {
                "has_structure": True,
                "has_references": True,
                # 약관에 "장단점"이 없으므로 한계 인정 답변 예상
            }
        },
        {
            "name": "구체적 질의 - 조항 번호 포함",
            "query": "제15조의 내용이 무엇인가요?",
            "expected_validation": {
                "has_structure": True,
                "has_references": True,
                "has_clause_numbers": True
            }
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"테스트: {test_case['name']}")
        logger.info(f"질의: {test_case['query']}")
        logger.info(f"{'=' * 80}")
        
        try:
            # 그래프 실행
            final_state = await run_graph(query=test_case["query"])
            
            # 결과 추출
            final_answer = final_state.get("final_answer", "")
            task_results = final_state.get("task_results", {})
            answer_results = task_results.get("answer", {})
            validation = answer_results.get("validation", {})
            
            # 결과 출력
            logger.info(f"\n📝 생성된 답변:\n{final_answer}\n")
            
            # 검증 결과
            logger.info(f"✅ 검증 결과:")
            logger.info(f"  - 구조화: {validation.get('has_structure', False)}")
            logger.info(f"  - 참조 인용: {validation.get('has_references', False)}")
            logger.info(f"  - 조항 번호: {validation.get('has_clause_numbers', False)}")
            
            if validation.get("warnings"):
                logger.warning(f"⚠️ 경고 사항:")
                for warning in validation["warnings"]:
                    logger.warning(f"  - {warning}")
            
            # 기대값과 비교
            expected = test_case.get("expected_validation", {})
            passed = True
            
            for key in ["has_structure", "has_references"]:
                if key in expected:
                    if validation.get(key) != expected[key]:
                        logger.error(f"❌ {key}: 기대={expected[key]}, 실제={validation.get(key)}")
                        passed = False
            
            results.append({
                "test_case": test_case["name"],
                "passed": passed,
                "validation": validation
            })
            
            if passed:
                logger.info("✅ 테스트 통과")
            else:
                logger.error("❌ 테스트 실패")
        
        except Exception as e:
            logger.error(f"❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "test_case": test_case["name"],
                "passed": False,
                "error": str(e)
            })
    
    # 전체 결과 요약
    logger.info(f"\n{'=' * 80}")
    logger.info("테스트 결과 요약")
    logger.info(f"{'=' * 80}")
    
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    
    for result in results:
        status = "✅ 통과" if result["passed"] else "❌ 실패"
        logger.info(f"{status}: {result['test_case']}")
    
    logger.info(f"\n통과율: {passed_count}/{total_count} ({passed_count/total_count*100:.1f}%)")
    
    if passed_count == total_count:
        logger.info("🎉 모든 테스트 통과!")
    else:
        logger.warning(f"⚠️ {total_count - passed_count}개 테스트 실패")


async def test_answer_validation():
    """답변 검증 로직 단위 테스트"""
    logger.info(f"\n{'=' * 80}")
    logger.info("답변 검증 로직 단위 테스트")
    logger.info(f"{'=' * 80}")
    
    from agents.answer_agent import AnswerAgent
    
    agent = AnswerAgent()
    
    # 테스트 케이스
    test_answers = [
        {
            "name": "완벽한 답변",
            "answer": """**📌 답변**
암 진단비는 3,000만원입니다 [참조 1, 제5조].

**📋 관련 약관**
- [참조 1] 제5조: 암 진단 시 보험금 지급

**⚠️ 주의사항**
갑상선암은 제외됩니다.""",
            "search_results": [{"clause_number": "제5조"}],
            "expected": {
                "has_structure": True,
                "has_references": True,
                "has_clause_numbers": True,
                "warnings": []
            }
        },
        {
            "name": "참조 없는 답변",
            "answer": """**📌 답변**
암 진단비는 3,000만원입니다.

**📋 관련 약관**
- 제5조: 암 진단 시 보험금 지급""",
            "search_results": [{"clause_number": "제5조"}],
            "expected": {
                "has_structure": True,
                "has_references": False,
                "has_clause_numbers": True,
                "warnings": ["참조 번호가 포함되지 않았습니다"]
            }
        },
        {
            "name": "구조 없는 답변",
            "answer": "암 진단비는 3,000만원입니다 [참조 1, 제5조].",
            "search_results": [{"clause_number": "제5조"}],
            "expected": {
                "has_structure": False,
                "has_references": True,
                "has_clause_numbers": True,
                "warnings": ["구조화된 형식이 없습니다"]
            }
        }
    ]
    
    for test in test_answers:
        logger.info(f"\n테스트: {test['name']}")
        
        validation = agent.validate_answer(
            test["answer"],
            test["search_results"]
        )
        
        logger.info(f"검증 결과: {validation}")
        
        expected = test["expected"]
        passed = (
            validation["has_structure"] == expected["has_structure"] and
            validation["has_references"] == expected["has_references"] and
            validation["has_clause_numbers"] == expected["has_clause_numbers"]
        )
        
        if passed:
            logger.info("✅ 통과")
        else:
            logger.error(f"❌ 실패")
            logger.error(f"  기대: {expected}")
            logger.error(f"  실제: {validation}")


async def main():
    """메인 테스트 실행"""
    try:
        # 단위 테스트 (빠름)
        await test_answer_validation()
        
        # 통합 테스트 (느림 - OpenAI API 호출)
        logger.info(f"\n{'=' * 80}")
        logger.info("통합 테스트를 실행하시겠습니까? (OpenAI API 사용)")
        logger.info(f"{'=' * 80}")
        
        # 자동으로 실행 (테스트 환경)
        await test_hallucination_prevention()
        
    except Exception as e:
        logger.error(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

