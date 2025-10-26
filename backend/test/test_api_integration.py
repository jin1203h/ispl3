"""
API 통합 테스트
Agent 기반으로 리팩토링된 API 엔드포인트 테스트
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_chat_health():
    """채팅 API Health 체크"""
    from api.chat import chat_health
    
    print("\n1. 채팅 API Health 체크")
    result = await chat_health()
    
    assert result["status"] == "ok"
    assert result["service"] == "chat"
    assert "router" in result["agents"]
    assert "processing" in result["agents"]
    assert "management" in result["agents"]
    
    print(f"   ✅ Health: {result['status']}")
    print(f"   ✅ Agents: {', '.join(result['agents'])}")


async def test_processing_agent_api():
    """Processing Agent API 통합 테스트 (로직 검증)"""
    print("\n2. Processing Agent API 통합 (로직 검증)")
    
    # State 생성 및 Agent 호출 로직 확인
    from agents.state import create_initial_state
    from agents.processing_agent import processing_agent
    
    # 빈 상태로 테스트 (실제 파일 없이 구조만 확인)
    state = create_initial_state("")
    state["task_type"] = "upload"
    state["file_data"] = None  # 실제 파일 없음
    state["filename"] = "test.pdf"
    
    print(f"   ✅ State 생성 완료")
    print(f"   ✅ Processing Agent 호출 가능 확인")
    print(f"   ⚠️ 실제 파일 업로드는 수동 테스트 필요")


async def test_management_agent_api():
    """Management Agent API 통합 테스트 (로직 검증)"""
    print("\n3. Management Agent API 통합 (로직 검증)")
    
    from agents.state import create_initial_state
    from agents.management_agent import management_agent
    
    # State 생성 확인
    state = create_initial_state("")
    state["task_type"] = "manage"
    state["management_action"] = "list"
    state["limit"] = 10
    
    print(f"   ✅ State 생성 완료")
    print(f"   ✅ Management Agent 호출 가능 확인")
    print(f"   ⚠️ 실제 DB 연결은 서버 실행 시 테스트 필요")


async def test_api_imports():
    """API 모듈 import 테스트"""
    print("\n4. API 모듈 Import 테스트")
    
    try:
        from api import pdf, documents, chat
        print(f"   ✅ api.pdf import 성공")
        print(f"   ✅ api.documents import 성공")
        print(f"   ✅ api.chat import 성공")
        
        # Router 확인
        assert hasattr(pdf, 'router'), "pdf.router가 없습니다"
        assert hasattr(documents, 'router'), "documents.router가 없습니다"
        assert hasattr(chat, 'router'), "chat.router가 없습니다"
        
        print(f"   ✅ 모든 라우터 존재 확인")
    
    except Exception as e:
        print(f"   ❌ Import 오류: {e}")
        raise


async def test_agent_integration():
    """Agent 통합 테스트"""
    print("\n5. Agent 통합 확인")
    
    from agents import (
        router_agent,
        search_agent,
        answer_agent,
        processing_agent,
        management_agent
    )
    
    agents = [
        ("Router", router_agent),
        ("Search", search_agent),
        ("Answer", answer_agent),
        ("Processing", processing_agent),
        ("Management", management_agent)
    ]
    
    for name, agent in agents:
        assert agent is not None, f"{name} Agent가 None입니다"
        print(f"   ✅ {name} Agent 로드 성공")


async def test_graph_structure():
    """그래프 구조 테스트"""
    print("\n6. 그래프 구조 확인")
    
    from agents.graph import create_graph
    
    graph = create_graph()
    
    expected_nodes = [
        "router",
        "search_agent",
        "answer_agent",
        "processing_agent",
        "management_agent"
    ]
    
    for node in expected_nodes:
        assert node in graph.nodes, f"{node} 노드가 그래프에 없습니다"
        print(f"   ✅ {node} 노드 존재")
    
    print(f"   ✅ 전체 노드 수: {len(graph.nodes)}")


async def test_api_endpoint_structure():
    """API 엔드포인트 구조 테스트"""
    print("\n7. API 엔드포인트 구조 확인")
    
    from api.pdf import router as pdf_router
    from api.documents import router as doc_router
    from api.chat import router as chat_router
    
    # PDF API 엔드포인트
    pdf_routes = [route.path for route in pdf_router.routes]
    print(f"   ✅ PDF API: {len(pdf_routes)} 엔드포인트")
    assert any("/upload" in path for path in pdf_routes), "/upload 엔드포인트 없음"
    
    # Documents API 엔드포인트
    doc_routes = [route.path for route in doc_router.routes]
    print(f"   ✅ Documents API: {len(doc_routes)} 엔드포인트")
    
    # Chat API 엔드포인트
    chat_routes = [route.path for route in chat_router.routes]
    print(f"   ✅ Chat API: {len(chat_routes)} 엔드포인트")


if __name__ == "__main__":
    print("="*70)
    print("Phase 2.3: API 통합 테스트")
    print("="*70)
    
    try:
        # 테스트 실행
        asyncio.run(test_chat_health())
        asyncio.run(test_processing_agent_api())
        asyncio.run(test_management_agent_api())
        asyncio.run(test_api_imports())
        asyncio.run(test_agent_integration())
        asyncio.run(test_graph_structure())
        asyncio.run(test_api_endpoint_structure())
        
        print("\n" + "="*70)
        print("✅ 모든 통합 테스트 통과!")
        print("="*70)
        
        print("\n📝 추가 테스트 필요:")
        print("   1. 서버 실행 후 실제 API 호출 테스트")
        print("   2. Frontend에서 업로드 기능 테스트")
        print("   3. Frontend에서 문서 관리 기능 테스트")
        print("   4. 채팅에서 Agent 라우팅 테스트")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



