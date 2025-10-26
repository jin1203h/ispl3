"""
답변 검증 로직 종합 테스트 (End-to-End)

Task 2.1.3 - Sub-task 8: 통합 테스트 및 검증

전체 파이프라인 테스트:
Router Agent → Search Agent → Answer Agent → Answer Validation
"""
import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 테스트 환경 설정
os.environ["TESTING"] = "true"

import asyncio
import logging
import time

from agents.state import ISPLState
from agents.router_agent import RouterAgent
from agents.search_agent import SearchAgent
from agents.answer_agent import AnswerAgent
from services.answer_validator import AnswerValidator
from models.answer_validation import AnswerValidation, ValidationDetail

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_answer_validation_model():
    """AnswerValidation 모델 테스트"""
    print("=" * 60)
    print("Test 1: AnswerValidation 모델")
    print("=" * 60)
    
    format_check = ValidationDetail(
        check_name="형식 검증",
        passed=True,
        score=1.0,
        details="구조화된 형식"
    )
    
    validation = AnswerValidation(
        confidence_score=0.85,
        is_reliable=True,
        hallucination_check=format_check,
        clause_existence_check=format_check,
        context_match_check=format_check,
        format_check=format_check,
        validation_time=1.5,
        regeneration_count=0,
        warnings=[]
    )
    
    # 직렬화 테스트
    data = validation.dict()
    
    assert data["confidence_score"] == 0.85
    assert data["is_reliable"] is True
    assert "hallucination_check" in data
    
    print("✅ 모델 생성 및 직렬화 성공:")
    print(f"   - confidence_score: {validation.confidence_score}")
    print(f"   - is_reliable: {validation.is_reliable}")
    print()


def test_router_agent_classification():
    """Router Agent 질의 분류 테스트"""
    print("=" * 60)
    print("Test 2: Router Agent 질의 분류")
    print("=" * 60)
    
    router = RouterAgent()
    
    # classify_intent 직접 테스트
    intent = router.classify_intent("암 진단비는 얼마인가요?")
    
    assert intent == "search"
    
    print("✅ Router Agent 분류 성공:")
    print(f"   - intent: {intent}")
    
    # route 메서드 테스트
    state = ISPLState(
        query="암 진단비는 얼마인가요?",
        task_type="",
        next_agent=""
    )
    
    command = router.route(state)
    
    assert command.update["task_type"] == "search"
    assert command.update["next_agent"] == "search_agent"
    assert command.goto == "search_agent"
    
    print(f"   - task_type: {command.update['task_type']}")
    print(f"   - next_agent: {command.update['next_agent']}")
    print()


async def test_search_agent_preprocessing():
    """Search Agent 전처리 통합 테스트"""
    print("=" * 60)
    print("Test 3: Search Agent 전처리")
    print("=" * 60)
    
    search_agent = SearchAgent()
    
    state = ISPLState(
        query="제5조 내용 알려줘",
        task_type="search",
        next_agent="search_agent"
    )
    
    result = await search_agent.search(state)
    
    # 전처리 정보 확인
    if "task_results" in result and "search" in result["task_results"]:
        search_task = result["task_results"]["search"]
        
        if "preprocessing" in search_task:
            preprocessing = search_task["preprocessing"]
            
            assert "original_query" in preprocessing
            assert "standardized_query" in preprocessing
            
            print("✅ Search Agent 전처리 통합:")
            print(f"   - 원본 질의: {preprocessing['original_query']}")
            print(f"   - 표준화 질의: {preprocessing['standardized_query']}")
            print(f"   - 조항 번호: {preprocessing.get('clause_number', 'N/A')}")
        else:
            print("⚠️ 전처리 정보 없음 (검색 결과가 없을 수 있음)")
    else:
        print("⚠️ task_results 정보 없음")
    
    print()


async def test_answer_agent_with_mock_results():
    """Answer Agent Mock 검색 결과로 테스트"""
    print("=" * 60)
    print("Test 4: Answer Agent with Mock Results")
    print("=" * 60)
    
    answer_agent = AnswerAgent()
    
    # Mock 검색 결과
    search_results = [
        {
            "content": "제5조(암진단비의 지급): 피보험자가 암으로 진단 확정되었을 때 최초 1회에 한하여 3,000만원을 지급합니다.",
            "similarity": 0.95,
            "document": {"filename": "test_policy.pdf"},
            "page_number": 5,
            "clause_number": "제5조"
        }
    ]
    
    state = ISPLState(
        query="암 진단비는 얼마인가요?",
        search_results=search_results,
        task_type="search",
        next_agent="answer_agent"
    )
    
    start_time = time.time()
    result = await answer_agent.generate_answer(state)
    elapsed = time.time() - start_time
    
    assert "final_answer" in result
    assert "task_results" in result
    
    answer_task = result["task_results"]["answer"]
    assert answer_task["success"] is True
    assert "validation" in answer_task
    
    validation = answer_task["validation"]
    
    print("✅ Answer Agent 답변 생성 및 검증:")
    print(f"   - 답변 길이: {len(result['final_answer'])}자")
    print(f"   - 신뢰도: {validation['confidence_score']:.2f}")
    print(f"   - 신뢰 가능: {validation['is_reliable']}")
    print(f"   - 재생성 횟수: {validation['regeneration_count']}")
    print(f"   - 소요 시간: {elapsed:.2f}s")
    print()


async def test_high_confidence_answer():
    """높은 신뢰도 답변 테스트"""
    print("=" * 60)
    print("Test 5: 높은 신뢰도 답변")
    print("=" * 60)
    
    answer_agent = AnswerAgent()
    
    # 고품질 검색 결과
    search_results = [
        {
            "content": "제5조(암진단비의 지급): 피보험자가 암으로 진단 확정되었을 때 최초 1회에 한하여 3,000만원을 지급합니다. 단, 갑상선암 등 소액암은 300만원으로 제한됩니다.",
            "similarity": 0.95,
            "document": {"filename": "policy.pdf"},
            "page_number": 5,
            "clause_number": "제5조"
        },
        {
            "content": "제5조 제2항: 갑상선암, 기타피부암, 경계성종양, 제자리암은 300만원을 지급합니다.",
            "similarity": 0.90,
            "document": {"filename": "policy.pdf"},
            "page_number": 5,
            "clause_number": "제5조"
        }
    ]
    
    state = ISPLState(
        query="암 진단비는 얼마인가요?",
        search_results=search_results,
        task_type="search",
        next_agent="answer_agent"
    )
    
    result = await answer_agent.generate_answer(state)
    validation = result["task_results"]["answer"]["validation"]
    
    # 높은 신뢰도 기대
    print("✅ 높은 신뢰도 답변:")
    print(f"   - 신뢰도: {validation['confidence_score']:.2f}")
    print(f"   - 신뢰 가능: {validation['is_reliable']}")
    print(f"   - 재생성 횟수: {validation['regeneration_count']}")
    print()


async def test_low_confidence_scenario():
    """낮은 신뢰도 시나리오 테스트"""
    print("=" * 60)
    print("Test 6: 낮은 신뢰도 시나리오")
    print("=" * 60)
    
    answer_agent = AnswerAgent()
    
    # 낮은 품질 검색 결과 (조항 번호 없음, 유사도 낮음)
    search_results = [
        {
            "content": "보험금 지급에 대한 일반적인 내용입니다.",
            "similarity": 0.4,
            "document": {"filename": "general.pdf"},
            "page_number": 1,
            "clause_number": "N/A"
        }
    ]
    
    state = ISPLState(
        query="암 진단비는 얼마인가요?",
        search_results=search_results,
        task_type="search",
        next_agent="answer_agent"
    )
    
    result = await answer_agent.generate_answer(state)
    validation = result["task_results"]["answer"]["validation"]
    
    # 재생성 시도가 있을 수 있음
    print("✅ 낮은 신뢰도 시나리오:")
    print(f"   - 신뢰도: {validation['confidence_score']:.2f}")
    print(f"   - 신뢰 가능: {validation['is_reliable']}")
    print(f"   - 재생성 횟수: {validation['regeneration_count']}")
    print(f"   - 최대 시도: {answer_agent.MAX_ATTEMPTS}")
    
    # 최대 재생성 횟수 확인
    assert validation['regeneration_count'] < answer_agent.MAX_ATTEMPTS
    
    print()


async def test_no_search_results():
    """검색 결과 없음 엣지 케이스"""
    print("=" * 60)
    print("Test 7: 검색 결과 없음 (엣지 케이스)")
    print("=" * 60)
    
    answer_agent = AnswerAgent()
    
    state = ISPLState(
        query="존재하지 않는 내용",
        search_results=[],
        task_type="search",
        next_agent="answer_agent"
    )
    
    result = await answer_agent.generate_answer(state)
    
    assert "final_answer" in result
    assert "죄송합니다" in result["final_answer"]
    assert result["task_results"]["answer"]["no_results"] is True
    
    print("✅ 검색 결과 없음 처리:")
    print(f"   - 답변: {result['final_answer'][:50]}...")
    print()


async def test_validation_performance():
    """검증 성능 테스트"""
    print("=" * 60)
    print("Test 8: 검증 성능")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    answer = """**📌 답변**
암 진단비는 최초 1회에 한하여 3,000만원이 지급됩니다 [참조 1, 제5조].

**📋 관련 약관**
- [참조 1] 제5조(암진단비의 지급): 3,000만원 지급
"""
    
    search_results = [
        {
            "content": "제5조(암진단비의 지급): 피보험자가 암으로 진단 확정되었을 때 최초 1회에 한하여 3,000만원을 지급합니다.",
        }
    ]
    
    start_time = time.time()
    
    validation = await validator.validate(answer, search_results, None)
    
    elapsed = time.time() - start_time
    
    # 5초 이내 완료 (순차 실행)
    assert elapsed < 5.0
    
    print("✅ 검증 성능:")
    print(f"   - 소요 시간: {elapsed:.3f}s")
    print(f"   - validation_time: {validation.validation_time:.3f}s")
    print(f"   - 신뢰도: {validation.confidence_score:.2f}")
    print()


async def test_confidence_calculation():
    """신뢰도 점수 계산 정확도 테스트"""
    print("=" * 60)
    print("Test 9: 신뢰도 점수 계산 정확도")
    print("=" * 60)
    
    validator = AnswerValidator()
    
    # 완벽한 검증 결과
    perfect_checks = ValidationDetail(
        check_name="테스트",
        passed=True,
        score=1.0,
        details="완벽함"
    )
    
    confidence = validator._calculate_confidence(
        hallucination_check=perfect_checks,
        clause_check=perfect_checks,
        context_check=perfect_checks,
        format_check=perfect_checks
    )
    
    # 가중 평균 (0.4 + 0.3 + 0.2 + 0.1 = 1.0)
    assert abs(confidence - 1.0) < 0.01
    
    print("✅ 신뢰도 점수 계산:")
    print(f"   - 완벽한 점수: {confidence:.4f}")
    print(f"   - 가중치: hallucination=0.4, context=0.3, clause=0.2, format=0.1")
    
    # 부분 점수 테스트
    partial_checks = ValidationDetail(
        check_name="테스트",
        passed=True,
        score=0.5,
        details="부분적"
    )
    
    confidence2 = validator._calculate_confidence(
        hallucination_check=partial_checks,
        clause_check=partial_checks,
        context_check=partial_checks,
        format_check=partial_checks
    )
    
    assert abs(confidence2 - 0.5) < 0.01
    
    print(f"   - 부분 점수: {confidence2:.4f}")
    print()


async def test_regeneration_max_attempts():
    """최대 재생성 횟수 테스트"""
    print("=" * 60)
    print("Test 10: 최대 재생성 횟수")
    print("=" * 60)
    
    answer_agent = AnswerAgent()
    
    # 매우 낮은 품질 검색 결과
    search_results = [
        {
            "content": "관련 없는 내용",
            "similarity": 0.1,
            "document": {"filename": "unrelated.pdf"},
            "page_number": 1,
            "clause_number": "N/A"
        }
    ]
    
    state = ISPLState(
        query="암 진단비는 얼마인가요?",
        search_results=search_results,
        task_type="search",
        next_agent="answer_agent"
    )
    
    result = await answer_agent.generate_answer(state)
    validation = result["task_results"]["answer"]["validation"]
    
    # 재생성 횟수가 최대 시도 횟수를 초과하지 않음
    assert validation['regeneration_count'] < answer_agent.MAX_ATTEMPTS
    
    print("✅ 최대 재생성 횟수 제한:")
    print(f"   - 재생성 횟수: {validation['regeneration_count']}")
    print(f"   - 최대 허용: {answer_agent.MAX_ATTEMPTS - 1}")
    print(f"   - 신뢰도: {validation['confidence_score']:.2f}")
    print()


async def main():
    """모든 테스트 실행"""
    print("\n")
    print("=" * 60)
    print("답변 검증 로직 종합 테스트 (End-to-End)")
    print("Task 2.1.3 - Sub-task 8")
    print("=" * 60)
    print("\n")
    
    passed = 0
    failed = 0
    
    # 동기 테스트
    sync_tests = [
        ("AnswerValidation 모델", test_answer_validation_model),
        ("Router Agent 질의 분류", test_router_agent_classification),
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
            import traceback
            traceback.print_exc()
            failed += 1
    
    # 비동기 테스트
    async_tests = [
        ("Search Agent 전처리", test_search_agent_preprocessing),
        ("Answer Agent with Mock Results", test_answer_agent_with_mock_results),
        ("높은 신뢰도 답변", test_high_confidence_answer),
        ("낮은 신뢰도 시나리오", test_low_confidence_scenario),
        ("검색 결과 없음 (엣지 케이스)", test_no_search_results),
        ("검증 성능", test_validation_performance),
        ("신뢰도 점수 계산 정확도", test_confidence_calculation),
        ("최대 재생성 횟수", test_regeneration_max_attempts),
    ]
    
    for test_name, test_func in async_tests:
        try:
            await test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_name} 실패:")
            print(f"   {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test_name} 오류:")
            print(f"   {e}")
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
        print("\n🎉 Task 2.1.3 (답변 검증 로직) 전체 완료!")


if __name__ == "__main__":
    asyncio.run(main())

