"""
데이터베이스 초기화 스크립트
schema.sql을 실행하여 테이블 생성
"""
import asyncio
import asyncpg
import sys
from pathlib import Path

# backend 루트 디렉토리를 Python 경로에 추가
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from core.config import settings


async def init_database():
    """데이터베이스 스키마 초기화"""
    # URL 파싱
    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    
    print(f"📊 데이터베이스 연결 중...")
    
    try:
        # asyncpg로 연결
        conn = await asyncpg.connect(db_url)
        
        print("✅ 데이터베이스 연결 성공")
        print("📄 schema.sql 읽는 중...")
        
        # schema.sql 읽기 (database 폴더 내에서)
        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        
        print("🔧 스키마 실행 중...")
        
        # SQL 실행
        await conn.execute(schema_sql)
        
        print("✅ 데이터베이스 스키마 초기화 완료!")
        
        # pgvector extension 확인
        result = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )
        
        if result:
            print("✅ pgvector extension 활성화 확인")
        else:
            print("⚠️  pgvector extension이 활성화되지 않았습니다.")
        
        # 테이블 목록 확인
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        
        print(f"\n📋 생성된 테이블 ({len(tables)}개):")
        for table in tables:
            print(f"  - {table['tablename']}")
        
        await conn.close()
        print("\n🎉 데이터베이스 초기화 완료!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(init_database())
