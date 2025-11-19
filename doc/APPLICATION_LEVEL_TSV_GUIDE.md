# content_tsv 애플리케이션 레벨 관리 가이드

## 개요

`content_tsv` 컬럼은 트리거를 사용하지 않고 애플리케이션 레벨에서 관리합니다.

## 장점

- ✅ 명시적인 로직 (디버깅 용이)
- ✅ 성능 제어 가능 (선택적 업데이트)
- ✅ 테스트 용이
- ✅ 트리거 의존성 제거

## 구현 방법

### 1. chunk_repository.py에 헬퍼 함수 추가

```python
# backend/services/chunk_repository.py
from sqlalchemy import text

def generate_tsvector(content: str) -> str:
    """
    content를 tsvector로 변환하는 SQL 표현식 생성
    
    Args:
        content: 텍스트 내용
    
    Returns:
        SQL 표현식 문자열
    """
    return f"to_tsvector('simple', '{content.replace(\"'\", \"''\")}')"
```

### 2. INSERT 시 content_tsv 생성

**방법 A: Raw SQL (권장)**

```python
# backend/services/chunk_repository.py
async def save_chunks(session: AsyncSession, chunks: List[Chunk]):
    """청크를 DB에 저장"""
    for chunk in chunks:
        # Raw SQL로 INSERT (content_tsv 자동 생성)
        query = text("""
            INSERT INTO document_chunks 
            (document_id, content, embedding, content_tsv, chunk_type, page_number, ...)
            VALUES 
            (:document_id, :content, :embedding, 
             to_tsvector('simple', :content),  -- content_tsv 생성
             :chunk_type, :page_number, ...)
        """)
        
        await session.execute(query, {
            "document_id": chunk.document_id,
            "content": chunk.content,
            "embedding": chunk.embedding,
            "chunk_type": chunk.chunk_type,
            "page_number": chunk.page_number,
            # ...
        })
    
    await session.commit()
```

**방법 B: SQLAlchemy ORM + 별도 UPDATE**

```python
# backend/services/chunk_repository.py
async def save_chunks(session: AsyncSession, chunks: List[Chunk]):
    """청크를 DB에 저장"""
    for chunk in chunks:
        # 1. ORM으로 INSERT
        db_chunk = DocumentChunk(
            document_id=chunk.document_id,
            content=chunk.content,
            embedding=chunk.embedding,
            chunk_type=chunk.chunk_type,
            # content_tsv는 NULL
        )
        session.add(db_chunk)
    
    await session.flush()  # ID 생성
    
    # 2. content_tsv 일괄 업데이트
    await session.execute(text("""
        UPDATE document_chunks 
        SET content_tsv = to_tsvector('simple', content)
        WHERE content_tsv IS NULL
    """))
    
    await session.commit()
```

### 3. UPDATE 시 content_tsv 갱신

```python
# backend/services/chunk_repository.py
async def update_chunk_content(
    session: AsyncSession,
    chunk_id: int,
    new_content: str
):
    """청크 내용 수정"""
    # Raw SQL로 content와 content_tsv를 동시에 업데이트
    query = text("""
        UPDATE document_chunks 
        SET 
            content = :new_content,
            content_tsv = to_tsvector('simple', :new_content)
        WHERE id = :chunk_id
    """)
    
    await session.execute(query, {
        "new_content": new_content,
        "chunk_id": chunk_id
    })
    
    await session.commit()
```

### 4. 기존 데이터 마이그레이션 (필요 시)

```python
# 기존 청크에 content_tsv 추가 (한 번만 실행)
async def migrate_existing_chunks(session: AsyncSession):
    """기존 청크에 content_tsv 생성"""
    result = await session.execute(text("""
        UPDATE document_chunks 
        SET content_tsv = to_tsvector('simple', content)
        WHERE content_tsv IS NULL
    """))
    
    await session.commit()
    
    print(f"✅ {result.rowcount}개 청크 마이그레이션 완료")
```

## 통합 예시

### PDF 처리 파이프라인에 통합

```python
# backend/services/pdf_processor.py
class PDFProcessor:
    async def process_pdf(self, pdf_path: str, document_id: int):
        # ... PDF 처리 로직 ...
        
        # 청크 저장 (content_tsv 포함)
        await self.chunk_repository.save_chunks_with_tsv(
            session=session,
            chunks=chunks
        )
```

### chunk_repository.py 전체 구현 예시

```python
# backend/services/chunk_repository.py
from typing import List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from services.chunker import Chunk

class ChunkRepository:
    """청크 저장소"""
    
    async def save_chunks_with_tsv(
        self,
        session: AsyncSession,
        chunks: List[Chunk]
    ):
        """
        청크를 저장하면서 content_tsv도 생성
        
        Args:
            session: DB 세션
            chunks: 저장할 청크 리스트
        """
        for chunk in chunks:
            query = text("""
                INSERT INTO document_chunks 
                (document_id, content, embedding, content_tsv, 
                 chunk_type, page_number, section_title, 
                 clause_number, token_count, metadata)
                VALUES 
                (:document_id, :content, :embedding, 
                 to_tsvector('simple', :content),
                 :chunk_type, :page_number, :section_title,
                 :clause_number, :token_count, :metadata)
            """)
            
            await session.execute(query, {
                "document_id": chunk.document_id,
                "content": chunk.content,
                "embedding": chunk.embedding,
                "chunk_type": chunk.chunk_type,
                "page_number": chunk.page_number,
                "section_title": chunk.section_title,
                "clause_number": chunk.clause_number,
                "token_count": chunk.token_count,
                "metadata": chunk.metadata
            })
        
        await session.commit()
        print(f"✅ {len(chunks)}개 청크 저장 완료 (content_tsv 포함)")
```

## 주의사항

### 1. SQL Injection 방지

```python
# ❌ 나쁜 예
query = f"INSERT INTO ... VALUES (to_tsvector('simple', '{content}'))"

# ✅ 좋은 예 (파라미터 바인딩)
query = text("INSERT INTO ... VALUES (to_tsvector('simple', :content))")
await session.execute(query, {"content": content})
```

### 2. 일관성 유지

모든 INSERT/UPDATE에서 content_tsv를 함께 처리해야 합니다:
- ✅ PDF 업로드 시
- ✅ 청크 수정 시
- ✅ 수동 데이터 입력 시

### 3. 성능 최적화

대량 INSERT 시 배치 처리:

```python
# 배치 INSERT
values = [
    {
        "content": chunk.content,
        "embedding": chunk.embedding,
        # ...
    }
    for chunk in chunks
]

query = text("""
    INSERT INTO document_chunks 
    (content, embedding, content_tsv, ...)
    VALUES 
    (:content, :embedding, to_tsvector('simple', :content), ...)
""")

await session.execute(query, values)
```

## 검증

### 테스트 코드

```python
# backend/test/test_chunk_repository.py
async def test_save_chunks_creates_tsvector():
    """청크 저장 시 content_tsv가 생성되는지 확인"""
    chunk = Chunk(content="암 진단비는 3000만원")
    
    await chunk_repository.save_chunks_with_tsv(session, [chunk])
    
    # content_tsv 확인
    result = await session.execute(text("""
        SELECT content_tsv IS NOT NULL as has_tsv
        FROM document_chunks
        WHERE content = '암 진단비는 3000만원'
    """))
    
    assert result.scalar() == True
```

## 롤백 방법

트리거 방식으로 돌아가려면:

```sql
-- 1. 트리거 생성
CREATE TRIGGER tsvector_update 
BEFORE INSERT OR UPDATE ON document_chunks 
FOR EACH ROW EXECUTE FUNCTION update_content_tsv();

-- 2. 애플리케이션 코드에서 content_tsv 생성 로직 제거
```

## 요약

- ✅ **INSERT**: Raw SQL로 `to_tsvector('simple', :content)` 사용
- ✅ **UPDATE**: content와 content_tsv 동시 업데이트
- ✅ **테스트**: content_tsv IS NOT NULL 확인
- ✅ **성능**: 배치 처리 활용

