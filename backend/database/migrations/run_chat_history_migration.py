"""
대화 이력 테이블 추가 마이그레이션 실행
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from core.database import get_engine


async def run_migration():
    """대화 이력 마이그레이션 실행"""
    engine = get_engine()
    
    # 마이그레이션 SQL 파일 읽기
    migration_file = Path(__file__).parent / "add_chat_history.sql"
    
    if not migration_file.exists():
        print(f"❌ 마이그레이션 파일을 찾을 수 없습니다: {migration_file}")
        return False
    
    migration_sql = migration_file.read_text(encoding="utf-8")
    
    print("🚀 대화 이력 테이블 마이그레이션 시작...")
    print(f"📄 파일: {migration_file.name}")
    print("-" * 60)
    
    try:
        async with engine.begin() as conn:
            # SQL을 스마트하게 분리 (함수/트리거 정의는 하나의 블록으로)
            statements = []
            current_statement = []
            in_function = False
            
            for line in migration_sql.split('\n'):
                line_stripped = line.strip()
                
                # 주석이나 빈 줄은 건너뛰기
                if not line_stripped or line_stripped.startswith('--'):
                    continue
                
                # 함수 정의 시작
                if 'CREATE OR REPLACE FUNCTION' in line:
                    if current_statement:
                        statements.append('\n'.join(current_statement))
                        current_statement = []
                    in_function = True
                    current_statement.append(line)
                # 함수 정의 종료
                elif in_function and line_stripped.startswith('$$'):
                    current_statement.append(line)
                    if '$$' in line and line.count('$$') == 2:
                        # $$ LANGUAGE plpgsql 형식
                        statements.append('\n'.join(current_statement))
                        current_statement = []
                        in_function = False
                    elif line_stripped == '$$':
                        # 다음 라인 확인 필요
                        pass
                elif in_function and 'LANGUAGE plpgsql' in line:
                    current_statement.append(line)
                    statements.append('\n'.join(current_statement))
                    current_statement = []
                    in_function = False
                # 일반 문장
                elif not in_function:
                    current_statement.append(line)
                    if line_stripped.endswith(';'):
                        statements.append('\n'.join(current_statement))
                        current_statement = []
                else:
                    current_statement.append(line)
            
            # 남은 문장 처리
            if current_statement:
                statements.append('\n'.join(current_statement))
            
            # 각 문장 실행
            for i, statement in enumerate(statements, 1):
                stmt = statement.strip()
                if stmt and not stmt.startswith('--'):
                    print(f"[{i}/{len(statements)}] 실행 중...")
                    # 세미콜론 제거 (text()는 세미콜론 불필요)
                    stmt = stmt.rstrip(';')
                    await conn.execute(text(stmt))
                    print(f"✅ 완료")
        
        print("-" * 60)
        print("✅ 마이그레이션 완료!")
        print()
        print("추가된 테이블:")
        print("  - chat_sessions (대화 세션)")
        print("  - chat_messages (대화 메시지)")
        print()
        print("참고: 트리거 없이 애플리케이션 레벨에서 관리")
        return True
        
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


async def verify_migration():
    """마이그레이션 검증"""
    engine = get_engine()
    
    print()
    print("🔍 마이그레이션 검증 중...")
    
    try:
        async with engine.begin() as conn:
            # 테이블 존재 확인
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('chat_sessions', 'chat_messages')
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if len(tables) == 2:
                print("✅ 테이블 생성 확인:")
                for table in tables:
                    print(f"   - {table}")
            else:
                print(f"❌ 일부 테이블이 누락되었습니다: {tables}")
                return False
            
            # 인덱스 확인
            result = await conn.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE schemaname = 'public' 
                AND tablename IN ('chat_sessions', 'chat_messages')
                ORDER BY indexname
            """))
            indexes = [row[0] for row in result.fetchall()]
            
            print(f"✅ 인덱스 생성 확인: {len(indexes)}개")
            
            # 트리거 확인
            result = await conn.execute(text("""
                SELECT trigger_name 
                FROM information_schema.triggers 
                WHERE event_object_table IN ('chat_sessions', 'chat_messages')
                ORDER BY trigger_name
            """))
            triggers = [row[0] for row in result.fetchall()]
            
            if triggers:
                print(f"✅ 트리거 생성 확인:")
                for trigger in triggers:
                    print(f"   - {trigger}")
            
            print()
            print("✅ 검증 완료!")
            return True
            
    except Exception as e:
        print(f"❌ 검증 실패: {e}")
        return False
    finally:
        await engine.dispose()


async def main():
    """메인 함수"""
    print("=" * 60)
    print("  대화 이력 관리 테이블 마이그레이션")
    print("=" * 60)
    print()
    
    # 마이그레이션 실행
    success = await run_migration()
    
    if success:
        # 검증
        await verify_migration()
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

