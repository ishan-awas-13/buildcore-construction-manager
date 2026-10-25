import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

from sqlalchemy import create_engine, text

# We will test both databases: buildcore and buildcore_copy
DB_USER = 'postgres'
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'admin123')
DB_HOST = '127.0.0.1'
DB_PORT = '5432'

def compare_dbs():
    url_orig = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/buildcore"
    url_copy = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/buildcore_copy"

    eng_orig = create_engine(url_orig)
    eng_copy = create_engine(url_copy)

    print("=== TESTING CONNECTION TO buildcore_copy ===")
    try:
        with eng_copy.connect() as conn:
            ver = conn.execute(text("SELECT version();")).scalar()
            curr_db = conn.execute(text("SELECT current_database();")).scalar()
            print(f"Connected successfully to database: '{curr_db}'")
            print(f"PostgreSQL version: {ver[:60]}...")
    except Exception as e:
        print(f"FAILED to connect to buildcore_copy: {e}")
        return

    print("\n=== COMPARING TABLES ===")
    with eng_orig.connect() as conn_orig, eng_copy.connect() as conn_copy:
        tables_orig = set(r[0] for r in conn_orig.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)).fetchall())
        
        tables_copy = set(r[0] for r in conn_copy.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)).fetchall())

        all_tables = sorted(tables_orig | tables_copy)
        print(f"{'Table Name':<25} | {'buildcore':<12} | {'buildcore_copy':<14} | {'Match?'}")
        print("-" * 65)
        for t in all_tables:
            in_orig = t in tables_orig
            in_copy = t in tables_copy
            cnt_orig = conn_orig.execute(text(f"SELECT count(*) FROM {t}")).scalar() if in_orig else "N/A"
            cnt_copy = conn_copy.execute(text(f"SELECT count(*) FROM {t}")).scalar() if in_copy else "N/A"
            match = "YES" if cnt_orig == cnt_copy else "NO (MISMATCH)"
            print(f"{t:<25} | {str(cnt_orig):<12} | {str(cnt_copy):<14} | {match}")

        print("\n=== COMPARING VIEWS ===")
        views_orig = set(r[0] for r in conn_orig.execute(text("""
            SELECT table_name FROM information_schema.views WHERE table_schema = 'public'
        """)).fetchall())
        views_copy = set(r[0] for r in conn_copy.execute(text("""
            SELECT table_name FROM information_schema.views WHERE table_schema = 'public'
        """)).fetchall())
        all_views = sorted(views_orig | views_copy)
        print(f"{'View Name':<28} | {'buildcore':<10} | {'buildcore_copy':<14}")
        print("-" * 60)
        for v in all_views:
            print(f"{v:<28} | {'Present' if v in views_orig else 'MISSING':<10} | {'Present' if v in views_copy else 'MISSING':<14}")

        print("\n=== TESTING VIEWS IN buildcore_copy ===")
        for v in sorted(views_copy):
            try:
                cnt = conn_copy.execute(text(f"SELECT count(*) FROM {v}")).scalar()
                print(f"View '{v}': OK ({cnt} rows returned)")
            except Exception as e:
                print(f"View '{v}': ERROR -> {e}")

        print("\n=== TESTING SEQUENCES IN buildcore_copy ===")
        seqs = conn_copy.execute(text("""
            SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public'
        """)).fetchall()
        print(f"Sequences in buildcore_copy: {len(seqs)} found")

        print("\n=== TESTING CONSTRAINTS IN buildcore_copy ===")
        constraints = conn_copy.execute(text("""
            SELECT conrelid::regclass::text, conname, contype 
            FROM pg_constraint 
            WHERE connamespace = 'public'::regnamespace
        """)).fetchall()
        print(f"Constraints in buildcore_copy: {len(constraints)} found")

if __name__ == '__main__':
    compare_dbs()
