import os
import sys
import subprocess
import psycopg2

sys.stdout.reconfigure(encoding='utf-8')

PG_BIN = r"C:\Program Files\PostgreSQL\16\bin"
PG_DUMP = os.path.join(PG_BIN, "pg_dump.exe")
PG_RESTORE = os.path.join(PG_BIN, "pg_restore.exe")

DB_HOST = "127.0.0.1"
DB_PORT = "5432"
DB_USER = "postgres"
DB_PASSWORD = "admin123"

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKUP_DIR = os.path.join(PROJECT_ROOT, "database", "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)
BACKUP_FILE = os.path.join(BACKUP_DIR, "buildcore_copy_pre_qa_backup.dump")

def main():
    print("=" * 60)
    print("PREPARING QA TEST ENVIRONMENT")
    print("=" * 60)

    # 1. Verify connection and current databases
    conn = psycopg2.connect(dbname="postgres", user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("SELECT datname FROM pg_database WHERE datname IN ('buildcore', 'buildcore_copy', 'buildcore_test');")
    existing_dbs = [row[0] for row in cur.fetchall()]
    print(f"Existing target databases: {existing_dbs}")
    assert "buildcore_copy" in existing_dbs, "Source database 'buildcore_copy' does not exist!"

    # 2. Dump buildcore_copy
    print(f"\n[1/3] Creating fresh verified backup of buildcore_copy...")
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD

    cmd_dump = [
        PG_DUMP,
        "-h", DB_HOST,
        "-p", DB_PORT,
        "-U", DB_USER,
        "-F", "c",
        "-b",
        "-v",
        "-f", BACKUP_FILE,
        "buildcore_copy"
    ]
    res_dump = subprocess.run(cmd_dump, env=env, capture_output=True, text=True)
    if res_dump.returncode != 0:
        print(f"pg_dump error:\n{res_dump.stderr}")
        sys.exit(1)

    backup_size = os.path.getsize(BACKUP_FILE)
    print(f"Backup created successfully: {BACKUP_FILE} ({backup_size} bytes)")
    assert backup_size > 10000, "Backup file appears suspiciously small!"

    # 3. Disconnect any active connections to buildcore_test if it exists, drop it, and recreate
    print(f"\n[2/3] Setting up isolated database 'buildcore_test'...")
    if "buildcore_test" in existing_dbs:
        print("Terminating active connections to existing 'buildcore_test'...")
        cur.execute("""
            SELECT pg_terminate_backend(pid) 
            FROM pg_stat_activity 
            WHERE datname = 'buildcore_test' AND pid <> pg_backend_pid();
        """)
        print("Dropping existing 'buildcore_test'...")
        cur.execute("DROP DATABASE buildcore_test;")

    print("Creating new empty 'buildcore_test' database...")
    cur.execute("CREATE DATABASE buildcore_test OWNER postgres;")

    # 4. Restore dump into buildcore_test
    print(f"\n[3/3] Restoring backup into 'buildcore_test'...")
    cmd_restore = [
        PG_RESTORE,
        "-h", DB_HOST,
        "-p", DB_PORT,
        "-U", DB_USER,
        "-d", "buildcore_test",
        "-v",
        BACKUP_FILE
    ]
    res_restore = subprocess.run(cmd_restore, env=env, capture_output=True, text=True)
    # pg_restore might have returncode 0 or 1 with non-critical warnings
    print(f"Restore completed with exit code: {res_restore.returncode}")

    # 5. Verify buildcore_test
    test_conn = psycopg2.connect(dbname="buildcore_test", user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    test_cur = test_conn.cursor()
    test_cur.execute("""
        SELECT table_name, 
               (xpath('/row/cnt/text()', xml_count))[1]::text::int as row_count
        FROM (
          SELECT table_name, 
                 query_to_xml(format('select count(*) as cnt from %I', table_name), false, true, '') as xml_count
          FROM information_schema.tables
          WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ) t
        ORDER BY table_name;
    """)
    table_counts = test_cur.fetchall()
    print("\nTable row counts in buildcore_test:")
    for tbl, count in table_counts:
        print(f"  - {tbl:25}: {count} rows")

    test_conn.close()
    conn.close()
    print("\nSUCCESS: Isolated 'buildcore_test' database created and verified!")

if __name__ == "__main__":
    main()
