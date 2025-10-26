"""
청킹 및 임베딩 기능 테스트
"""
import sys
from pathlib import Path
import logging
import asyncio

# backend 루트를 Python 경로에 추가
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from services.chunker import TextChunker
from services.embedding_service import EmbeddingService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title: str):
    """섹션 제목 출력"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def test_text_chunker():
    """텍스트 청킹 기능 테스트"""
    print_section("텍스트 청킹 테스트")
    
    # Chunker 초기화
    chunker = TextChunker(chunk_size=100, overlap=20)
    
    # 테스트 텍스트
    test_text = """
# 보험 약관

## 제1조 (목적)
이 약관은 보험계약의 내용과 절차를 규정함을 목적으로 합니다.

## 제2조 (용어의 정의)
이 약관에서 사용하는 용어의 정의는 다음과 같습니다:
- 보험계약자: 보험회사와 계약을 체결하는 사람
- 피보험자: 보험 사고의 대상이 되는 사람
- 보험수익자: 보험금을 받을 수 있는 사람

| 구분 | 내용 |
|------|------|
| 보험료 | 월 50,000원 |
| 보장 기간 | 10년 |

## 제3조 (보험기간)
보험기간은 계약일로부터 10년으로 합니다.
    """
    
    # 1. 단순 텍스트 청킹
    print("\n1. 단순 텍스트 청킹:")
    chunks = chunker.chunk_text(test_text, document_id=1)
    print(f"  - 생성된 청크 수: {len(chunks)}")
    print(f"  - 총 토큰 수: {sum(c.token_count for c in chunks)}")
    
    for i, chunk in enumerate(chunks[:3]):  # 처음 3개만 출력
        print(f"\n  [청크 {i+1}]")
        print(f"  - 토큰 수: {chunk.token_count}")
        print(f"  - 타입: {chunk.chunk_type}")
        print(f"  - 내용 미리보기: {chunk.content[:100]}...")
    
    # 2. Markdown 청킹 (표 분리)
    print("\n\n2. Markdown 청킹 (표 감지):")
    md_chunks = chunker.chunk_markdown(test_text, document_id=1)
    print(f"  - 생성된 청크 수: {len(md_chunks)}")
    print(f"  - 텍스트 청크: {sum(1 for c in md_chunks if c.chunk_type == 'text')}")
    print(f"  - 표 청크: {sum(1 for c in md_chunks if c.chunk_type == 'table')}")
    
    # 표 청크 출력
    table_chunks = [c for c in md_chunks if c.chunk_type == 'table']
    if table_chunks:
        print("\n  [표 청크]")
        for tc in table_chunks:
            print(f"  - 토큰 수: {tc.token_count}")
            print(f"  - 내용:\n{tc.content}")
    
    # 3. 메타데이터 추출 확인
    print("\n\n3. 메타데이터 추출:")
    for chunk in md_chunks[:3]:
        print(f"\n  [청크 {chunk.chunk_index + 1}]")
        print(f"  - 섹션: {chunk.section_title}")
        print(f"  - 조항: {chunk.clause_number}")
        print(f"  - 해시: {chunk.content_hash[:16]}...")


async def test_embedding_service():
    """임베딩 생성 기능 테스트"""
    print_section("임베딩 생성 테스트")
    
    # EmbeddingService 초기화
    embedding_service = EmbeddingService()
    
    # 1. 연결 테스트
    print("\n1. OpenAI API 연결 테스트:")
    is_connected = await embedding_service.test_connection()
    if not is_connected:
        print("  ❌ OpenAI API 연결 실패. 테스트를 중단합니다.")
        return
    
    # 2. 단일 임베딩 생성
    print("\n2. 단일 임베딩 생성:")
    test_text = "이 약관은 보험계약의 내용과 절차를 규정함을 목적으로 합니다."
    embedding = await embedding_service.create_embedding(test_text)
    print(f"  - 임베딩 차원: {len(embedding)}")
    print(f"  - 첫 5개 값: {embedding[:5]}")
    print(f"  - 유효성: {embedding_service.validate_embedding(embedding)}")
    
    # 3. 배치 임베딩 생성
    print("\n3. 배치 임베딩 생성:")
    texts = [
        "보험계약자는 보험회사와 계약을 체결하는 사람입니다.",
        "피보험자는 보험 사고의 대상이 되는 사람입니다.",
        "보험수익자는 보험금을 받을 수 있는 사람입니다."
    ]
    embeddings = await embedding_service.create_embeddings_batch(texts)
    print(f"  - 생성된 임베딩 수: {len(embeddings)}")
    print(f"  - 각 임베딩 차원: {[len(e) for e in embeddings]}")


async def test_db_save():
    """DB 저장 테스트"""
    print_section("벡터 DB 저장 테스트")
    
    from core.database import AsyncSessionLocal
    from services.chunk_repository import ChunkRepository
    from models.document import Document
    from datetime import date
    
    # 테스트 청크 생성
    print("\n1. 테스트 청크 생성...")
    chunker = TextChunker(chunk_size=100, overlap=20)
    test_text = """
# 제1조 (목적)
이 약관은 보험계약의 내용과 절차를 규정함을 목적으로 합니다.

## 제2조 (용어의 정의)
보험계약자는 보험회사와 계약을 체결하는 사람입니다.
    """
    
    chunks = chunker.chunk_markdown(test_text, document_id=9999)
    print(f"  - 생성된 청크: {len(chunks)}개")
    
    # 임베딩 생성
    print("\n2. 임베딩 생성...")
    embedding_service = EmbeddingService()
    chunks_with_embeddings = await embedding_service.create_chunk_embeddings(chunks)
    print(f"  - 임베딩 완료: {len(chunks_with_embeddings)}개")
    
    # DB 저장
    print("\n3. 벡터 DB 저장...")
    async with AsyncSessionLocal() as session:
        try:
            # 테스트용 Document 생성
            print("  - 테스트 Document 생성 중...")
            test_doc = Document(
                id=9999,
                filename="test_policy_9999.pdf",
                original_filename="테스트보험약관.pdf",
                file_path="/test/path.pdf",
                file_size=1024,
                document_type="policy",
                insurance_type="health",
                company_name="테스트보험",
                version="1.0",
                effective_date=date.today(),
                status="active",
                processing_status="completed",
                total_pages=10
            )
            session.add(test_doc)
            await session.commit()
            print("  ✅ Document 생성 완료")
            
            # 청크 저장
            chunk_repo = ChunkRepository(session)
            saved_chunks = await chunk_repo.save_chunks(
                chunks_with_embeddings,
                document_id=9999
            )
            print(f"  ✅ 청크 저장 완료: {len(saved_chunks)}개")
            
            # 저장 확인
            print("\n4. 저장 확인...")
            retrieved_chunks = await chunk_repo.get_chunks_by_document(9999)
            print(f"  - 조회된 청크: {len(retrieved_chunks)}개")
            
            if retrieved_chunks:
                sample = retrieved_chunks[0]
                print(f"\n  [샘플 청크]")
                print(f"  - ID: {sample.id}")
                print(f"  - 타입: {sample.chunk_type}")
                print(f"  - 토큰 수: {sample.token_count}")
                print(f"  - 임베딩 차원: {len(sample.embedding) if sample.embedding is not None else 0}")
                print(f"  - 내용 미리보기: {sample.content[:100]}...")
            
            # 정리
            print("\n5. 테스트 데이터 정리...")
            # Document 삭제하면 청크도 cascade로 삭제됨
            await session.delete(test_doc)
            await session.commit()
            print(f"  ✅ 정리 완료 (Document 및 관련 청크 삭제)")
            
        except Exception as e:
            await session.rollback()
            logger.exception(f"테스트 실패: {e}")
            print(f"  ❌ 오류: {e}")


async def test_integrated_chunking_and_embedding():
    """통합 테스트: 청킹 + 임베딩"""
    print_section("통합 테스트: 청킹 + 임베딩")
    
    # 테스트 Markdown 파일 읽기
    print("\nMarkdown 파일 경로를 입력하세요:")
    print("(예: uploads/documents/sample_policy_1.md)")
    md_path = input("경로: ").strip()
    
    if not Path(md_path).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {md_path}")
        return
    
    # Markdown 읽기
    with open(md_path, 'r', encoding='utf-8') as f:
        markdown_text = f.read()
    
    print(f"\n✅ Markdown 파일 로드 완료: {len(markdown_text)}자")
    
    # 청킹
    print("\n1. 텍스트 청킹...")
    chunker = TextChunker(chunk_size=1000, overlap=100)
    chunks = chunker.chunk_markdown(markdown_text, document_id=999)
    print(f"  - 생성된 청크 수: {len(chunks)}")
    print(f"  - 텍스트 청크: {sum(1 for c in chunks if c.chunk_type == 'text')}")
    print(f"  - 표 청크: {sum(1 for c in chunks if c.chunk_type == 'table')}")
    print(f"  - 총 토큰 수: {sum(c.token_count for c in chunks)}")
    
    # 임베딩 생성 여부 확인
    print("\n임베딩을 생성하시겠습니까? (y/n)")
    print("⚠️  주의: OpenAI API를 사용하므로 비용이 발생합니다.")
    choice = input("선택: ").strip().lower()
    
    if choice != 'y':
        print("\n임베딩 생성을 건너뜁니다.")
        return
    
    # 임베딩 생성
    print("\n2. 임베딩 생성 중... (시간이 걸릴 수 있습니다)")
    embedding_service = EmbeddingService()
    chunks_with_embeddings = await embedding_service.create_chunk_embeddings(chunks)
    
    print(f"\n✅ 임베딩 생성 완료!")
    print(f"  - 총 청크 수: {len(chunks_with_embeddings)}")
    
    # 결과 요약
    valid_count = sum(
        1 for c in chunks_with_embeddings 
        if 'embedding' in (c.metadata or {})
    )
    print(f"  - 유효한 임베딩: {valid_count}/{len(chunks_with_embeddings)}")
    
    # 샘플 출력
    if chunks_with_embeddings:
        print("\n샘플 청크 (첫 번째):")
        sample = chunks_with_embeddings[0]
        print(f"  - 인덱스: {sample.chunk_index}")
        print(f"  - 타입: {sample.chunk_type}")
        print(f"  - 토큰 수: {sample.token_count}")
        print(f"  - 내용 미리보기: {sample.content[:100]}...")
        print(f"  - 임베딩 차원: {len(sample.metadata.get('embedding', []))}")


async def main():
    """메인 함수"""
    print("\n" + "="*60)
    print(" ISPL - 청킹 및 임베딩 테스트")
    print("="*60)
    
    print("\n테스트 모드 선택:")
    print("1. 텍스트 청킹 테스트")
    print("2. 임베딩 생성 테스트")
    print("3. 벡터 DB 저장 테스트")
    print("4. 통합 테스트 (청킹 + 임베딩)")
    choice = input("선택 (1, 2, 3 또는 4): ").strip()
    
    if choice == "1":
        test_text_chunker()
    elif choice == "2":
        await test_embedding_service()
    elif choice == "3":
        await test_db_save()
    elif choice == "4":
        await test_integrated_chunking_and_embedding()
    else:
        print("잘못된 선택입니다.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n테스트 중단됨")
    except Exception as e:
        logger.exception(f"예상치 못한 오류: {e}")

