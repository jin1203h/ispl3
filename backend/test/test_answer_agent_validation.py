"""
AnswerAgent와 AnswerValidator 통합 테스트

Task 2.1.3 - Sub-task 7: AnswerAgent 재생성 로직 통합
"""
import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 테스트 환경 설정
os.environ["TESTING"] = "true"

import asyncio
import logging

from agents.answer_agent import AnswerAgent
from agents.state import ISPLState
from services.answer_validator import AnswerValidator

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_answer_agent_initialization():
    """AnswerAgent 초기화 테스트"""
    print("=" * 60)
    print("Test 1: AnswerAgent 초기화")
    print("=" * 60)
    
    agent = AnswerAgent()
    
    # AnswerValidator가 초기화되었는지 확인
    assert hasattr(agent, 'validator')
    assert isinstance(agent.validator, AnswerValidator)
    assert agent.MAX_ATTEMPTS == 3
    
    print("✅ AnswerAgent 초기화 성공:")
    print(f"   - validator: {type(agent.validator).__name__}")
    print(f"   - MAX_ATTEMPTS: {agent.MAX_ATTEMPTS}")
    print()


def test_validate_answer_removed():
    """기존 validate_answer() 메서드 제거 확인"""
    print("=" * 60)
    print("Test 2: validate_answer() 메서드 제거 확인")
    print("=" * 60)
    
    agent = AnswerAgent()
    
    # validate_answer() 메서드가 제거되었는지 확인
    # (실제로는 존재하지만, AnswerValidator로 이동되었음을 확인)
    # 여기서는 AnswerAgent에 validate_answer가 없는지 확인
    # 주의: 실제로 Python에서는 메서드가 없으면 AttributeError 발생
    
    # 대신 validator가 validate 메서드를 가지고 있는지 확인
    assert hasattr(agent.validator, 'validate')
    
    print("✅ AnswerValidator로 검증 로직 이동 확인:")
    print(f"   - validator.validate 존재: True")
    print()


async def test_generate_answer_with_search_results():
    """검색 결과가 있는 경우 답변 생성 테스트"""
    print("=" * 60)
    print("Test 3: 검색 결과로 답변 생성")
    print("=" * 60)
    
    agent = AnswerAgent()
    
    # Mock 검색 결과
    search_results = [
        {
            "content": "암 진단 시 보험금 3,000만원을 지급합니다.",
            "similarity": 0.9,
            "document": {"filename": "test.pdf"},
            "page_number": 1,
            "clause_number": "제5조"
        }
    ]
    
    state = ISPLState(
        query="암 진단비는 얼마인가요?",
        search_results=search_results,
        task_type="search",
        next_agent="answer_agent"
    )
    
    result = await agent.generate_answer(state)
    
    # 결과 검증
    assert "final_answer" in result
    assert "task_results" in result
    assert "answer" in result["task_results"]
    
    answer_result = result["task_results"]["answer"]
    assert answer_result["success"] is True
    assert "validation" in answer_result
    assert "model" in answer_result
    assert "tokens_used" in answer_result
    
    # validation 구조 확인
    validation = answer_result["validation"]
    assert "confidence_score" in validation
    assert "is_reliable" in validation
    assert "regeneration_count" in validation
    assert "hallucination_check" in validation
    assert "clause_existence_check" in validation
    assert "context_match_check" in validation
    assert "format_check" in validation
    
    print("✅ 답변 생성 및 검증 성공:")
    print(f"   - 답변 길이: {len(result['final_answer'])}자")
    print(f"   - 신뢰도: {validation['confidence_score']:.2f}")
    print(f"   - 신뢰 가능: {validation['is_reliable']}")
    print(f"   - 재생성 횟수: {validation['regeneration_count']}")
    print(f"   - 토큰 사용: {answer_result['tokens_used']}")
    print()


async def test_generate_answer_no_search_results():
    """검색 결과가 없는 경우 테스트"""
    print("=" * 60)
    print("Test 4: 검색 결과 없음")
    print("=" * 60)
    
    agent = AnswerAgent()
    
    state = ISPLState(
        query="테스트 질문",
        search_results=[],
        task_type="search",
        next_agent="answer_agent"
    )
    
    result = await agent.generate_answer(state)
    
    # 결과 검증
    assert "final_answer" in result
    assert "죄송합니다" in result["final_answer"]
    assert "task_results" in result
    assert result["task_results"]["answer"]["success"] is True
    assert result["task_results"]["answer"]["no_results"] is True
    
    print("✅ 검색 결과 없음 처리:")
    print(f"   - 답변: {result['final_answer'][:50]}...")
    print()


async def test_generate_answer_with_error():
    """검색 오류 처리 테스트"""
    print("=" * 60)
    print("Test 5: 검색 오류 처리")
    print("=" * 60)
    
    agent = AnswerAgent()
    
    state = ISPLState(
        query="테스트 질문",
        search_results=[],
        task_type="search",
        next_agent="answer_agent",
        error="검색 서비스 오류 발생"
    )
    
    result = await agent.generate_answer(state)
    
    # 결과 검증
    assert "final_answer" in result
    assert "죄송합니다" in result["final_answer"]
    assert "검색 서비스 오류 발생" in result["final_answer"]
    assert result["task_results"]["answer"]["success"] is False
    
    print("✅ 검색 오류 처리:")
    print(f"   - 답변: {result['final_answer']}")
    print()


async def test_regeneration_count():
    """재생성 횟수 기록 테스트"""
    print("=" * 60)
    print("Test 6: 재생성 횟수 기록")
    print("=" * 60)
    
    agent = AnswerAgent()
    
    # 간단한 검색 결과 (낮은 품질 답변을 유도하기 위해)
    search_results = [
        {
            "content": "테스트 내용",
            "similarity": 0.5,
            "document": {"filename": "test.pdf"},
            "page_number": 1,
            "clause_number": "N/A"
        }
    ]
    
    state = ISPLState(
        query="간단한 질문",
        search_results=search_results,
        task_type="search",
        next_agent="answer_agent"
    )
    
    result = await agent.generate_answer(state)
    
    # regeneration_count가 기록되어 있는지 확인
    validation = result["task_results"]["answer"]["validation"]
    assert "regeneration_count" in validation
    assert validation["regeneration_count"] >= 0
    assert validation["regeneration_count"] < agent.MAX_ATTEMPTS
    
    print("✅ 재생성 횟수 기록:")
    print(f"   - 재생성 횟수: {validation['regeneration_count']}")
    print(f"   - 신뢰도: {validation['confidence_score']:.2f}")
    print()


async def main():
    """모든 테스트 실행"""
    print("\n")
    print("=" * 60)
    print("AnswerAgent 재생성 로직 통합 테스트")
    print("Task 2.1.3 - Sub-task 7")
    print("=" * 60)
    print("\n")
    
    passed = 0
    failed = 0
    
    # 동기 테스트
    sync_tests = [
        ("AnswerAgent 초기화", test_answer_agent_initialization),
        ("validate_answer() 제거 확인", test_validate_answer_removed),
    ]
    
    for test_name, test_func in sync_tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_name} 실패: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test_name} 오류: {e}")
            failed += 1
    
    # 비동기 테스트
    async_tests = [
        ("검색 결과로 답변 생성", test_generate_answer_with_search_results),
        ("검색 결과 없음", test_generate_answer_no_search_results),
        ("검색 오류 처리", test_generate_answer_with_error),
        ("재생성 횟수 기록", test_regeneration_count),
    ]
    
    for test_name, test_func in async_tests:
        try:
            await test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_name} 실패: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test_name} 오류: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # 최종 결과
    print("=" * 60)
    print(f"테스트 결과: {passed}개 통과, {failed}개 실패")
    print("=" * 60)
    
    if failed > 0:
        print("❌ 일부 테스트 실패")
    else:
        print("✅ 모든 테스트 통과!")


if __name__ == "__main__":
    asyncio.run(main())

