"""
Full-Text Search 마이그레이션 실행 스크립트
add_fulltext_search.sql을 실행하여 tsvector 컬럼 및 인덱스 생성
"""
import asyncio
import asyncpg
import sys
from pathlib import Path

# backend 루트 디렉토리를 Python 경로에 추가
backend_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_root))

from core.config import settings


async def run_migration():
    """Full-Text Search 마이그레이션 실행"""
    # URL 파싱
    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    
    print(f"📊 데이터베이스 연결 중...")
    
    try:
        # asyncpg로 연결
        conn = await asyncpg.connect(db_url)
        
        print("✅ 데이터베이스 연결 성공")
        print("📄 add_fulltext_search.sql 읽는 중...")
        
        # add_fulltext_search.sql 읽기
        migration_path = Path(__file__).parent / "add_fulltext_search.sql"
        with open(migration_path, "r", encoding="utf-8") as f:
            migration_sql = f.read()
        
        print("🔧 마이그레이션 실행 중...")
        
        # SQL 실행
        # CONCURRENTLY 인덱스 생성은 트랜잭션 외부에서 실행되어야 하므로
        # 각 문장을 분리하여 실행
        
        # 1. 컬럼 추가
        await conn.execute("""
            ALTER TABLE document_chunks 
            ADD COLUMN IF NOT EXISTS content_tsv tsvector;
        """)
        print("  ✓ content_tsv 컬럼 추가")
        
        # 2. 인덱스 생성 (CONCURRENTLY는 별도 연결 필요)
        # asyncpg는 autocommit 모드이므로 CONCURRENTLY 실행 가능
        try:
            await conn.execute("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chunks_content_tsv 
                ON document_chunks USING GIN(content_tsv);
            """)
            print("  ✓ GIN 인덱스 생성 완료")
        except Exception as e:
            if "already exists" in str(e):
                print("  ℹ️  GIN 인덱스가 이미 존재합니다")
            else:
                raise
        
        print("  ℹ️  content_tsv는 애플리케이션에서 관리됩니다 (트리거 미사용)")
        
        print("\n🔍 마이그레이션 검증 중...")
        
        # 검증 1: content_tsv 컬럼 확인
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'document_chunks' 
                AND column_name = 'content_tsv'
            )
        """)
        if column_exists:
            print("  ✓ content_tsv 컬럼 생성 확인")
        else:
            print("  ⚠️  content_tsv 컬럼을 찾을 수 없습니다")
        
        # 검증 2: 인덱스 확인
        index_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE tablename = 'document_chunks' 
                AND indexname = 'idx_chunks_content_tsv'
            )
        """)
        if index_exists:
            print("  ✓ GIN 인덱스 생성 확인")
        else:
            print("  ⚠️  GIN 인덱스를 찾을 수 없습니다")
        
        await conn.close()
        print("\n✅ Full-Text Search 마이그레이션 완료!")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(run_migration())

