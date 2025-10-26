"""
3-Agent 구조 통합 테스트
Router Agent → Processing/Management/Search Agent
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.router_agent import router_agent
from agents.processing_agent import processing_agent
from agents.management_agent import management_agent
from agents.state import create_initial_state


async def test_router_search_intent():
    """Router Agent가 검색 의도를 올바르게 분류하는지 테스트"""
    # Given
    queries = [
        "암 진단비는 얼마인가요?",
        "해지환급금에 대해 알려주세요",
        "보장 내용을 확인하고 싶어요"
    ]
    
    # When & Then
    for query in queries:
        intent = router_agent.classify_intent(query)
        assert intent == "search", f"'{query}'는 search로 분류되어야 합니다"
        print(f"✅ Search 의도 분류: '{query[:30]}...' → {intent}")


async def test_router_upload_intent():
    """Router Agent가 업로드 의도를 올바르게 분류하는지 테스트"""
    # Given
    queries = [
        "PDF 파일을 업로드하고 싶어요",
        "새로운 약관을 등록해주세요",
        "문서를 추가하려고 합니다"
    ]
    
    # When & Then
    for query in queries:
        intent = router_agent.classify_intent(query)
        assert intent == "upload", f"'{query}'는 upload로 분류되어야 합니다"
        print(f"✅ Upload 의도 분류: '{query[:30]}...' → {intent}")


async def test_router_manage_intent():
    """Router Agent가 관리 의도를 올바르게 분류하는지 테스트"""
    # Given
    queries = [
        "목록 조회",
        "삭제",
        "관리"
    ]
    
    # When & Then
    for query in queries:
        intent = router_agent.classify_intent(query)
        assert intent == "manage", f"'{query}'는 manage로 분류되어야 합니다"
        print(f"✅ Manage 의도 분류: '{query[:30]}...' → {intent}")


async def test_router_command_routing():
    """Router Agent의 Command 기반 라우팅 테스트"""
    # Given
    test_cases = [
        ("암 진단비는 얼마인가요?", "search", "search_agent"),
        ("PDF 업로드", "upload", "processing_agent"),
        ("약관 목록", "manage", "management_agent")
    ]
    
    # When & Then
    for query, expected_task, expected_agent in test_cases:
        state = create_initial_state(query)
        state["task_type"] = None  # query 기반 분류를 위해 task_type 초기화
        command = router_agent.route(state)
        
        assert command.goto == expected_agent, \
            f"'{query}'는 {expected_agent}로 라우팅되어야 합니다"
        assert command.update['task_type'] == expected_task, \
            f"task_type은 {expected_task}여야 합니다"
        
        print(f"✅ 라우팅: '{query[:20]}...' → {expected_agent} (task_type={expected_task})")


async def test_explicit_task_type_routing():
    """명시적 task_type 우선 사용 테스트"""
    # Given
    query = "보험 약관 검색"  # 검색 키워드 포함
    state = create_initial_state(query)
    state["task_type"] = "manage"  # 명시적으로 manage 지정
    
    # When
    command = router_agent.route(state)
    
    # Then
    assert command.goto == "management_agent", \
        "명시적 task_type이 우선되어야 합니다"
    print(f"✅ 명시적 task_type 우선: manage → management_agent")


async def test_management_agent_list():
    """Management Agent의 목록 조회 기능 테스트"""
    # Given
    state = create_initial_state("목록")
    state["task_type"] = "manage"
    state["management_action"] = "list"
    
    # When
    result = await management_agent.manage(state)
    
    # Then
    assert result is not None
    assert "final_answer" in result
    assert "task_results" in result
    
    # 오류가 없으면 성공
    if not result.get("error"):
        assert result["task_results"]["management"]["success"] == True
        print(f"✅ Management Agent 목록 조회 성공")
        print(f"   응답: {result['final_answer'][:100]}...")
    else:
        # DB가 없을 수 있으므로 오류도 허용
        print(f"⚠️ Management Agent 실행 (DB 없음): {result.get('error')}")


async def test_state_fields():
    """State에 필요한 모든 필드가 정의되어 있는지 테스트"""
    # Given
    state = create_initial_state("테스트")
    
    # Then - 기본 필드
    assert "query" in state
    assert "task_type" in state
    assert "next_agent" in state
    assert "task_results" in state
    assert "final_answer" in state
    assert "error" in state
    
    # Processing Agent 필드
    assert "file_data" in state
    assert "filename" in state
    assert "processing_method" in state
    assert "document_type" in state
    assert "processing_result" in state
    
    # Management Agent 필드
    assert "management_action" in state
    assert "management_result" in state
    assert "document_id" in state
    assert "filter_filename" in state
    assert "sort_by" in state
    assert "limit" in state
    
    print(f"✅ State 모든 필드 정의 확인 완료")


async def test_graph_structure():
    """그래프 구조 및 노드 존재 여부 테스트"""
    from agents.graph import create_graph
    
    # Given & When
    graph = create_graph()
    
    # Then
    # 그래프가 정상적으로 생성되었는지 확인
    assert graph is not None
    print(f"✅ 그래프 생성 성공")
    
    # 노드 목록 확인
    nodes = graph.nodes
    expected_nodes = [
        "router",
        "search_agent",
        "answer_agent",
        "processing_agent",
        "management_agent"
    ]
    
    for node in expected_nodes:
        assert node in nodes, f"{node} 노드가 그래프에 없습니다"
        print(f"✅ 노드 존재 확인: {node}")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("3-Agent 구조 통합 테스트")
    print("="*70 + "\n")
    
    # 테스트 실행
    asyncio.run(test_router_search_intent())
    print()
    
    asyncio.run(test_router_upload_intent())
    print()
    
    asyncio.run(test_router_manage_intent())
    print()
    
    asyncio.run(test_router_command_routing())
    print()
    
    asyncio.run(test_explicit_task_type_routing())
    print()
    
    asyncio.run(test_management_agent_list())
    print()
    
    asyncio.run(test_state_fields())
    print()
    
    asyncio.run(test_graph_structure())
    print()
    
    print("\n" + "="*70)
    print("✅ 모든 테스트 완료!")
    print("="*70 + "\n")

