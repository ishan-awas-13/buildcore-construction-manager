import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

from app import create_app, db
from sqlalchemy import text

app = create_app()

def apply_migration(sql_filename):
    filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'migrations', sql_filename)
    if not os.path.exists(filepath):
        print(f"Error: Migration file not found: {filepath}")
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()

    with app.app_context():
        curr_db = db.session.execute(text("SELECT current_database();")).scalar()
        print(f"Applying migration '{sql_filename}' to active database: '{curr_db}'...")
        if curr_db == 'buildcore':
            print("CRITICAL SAFETY CHECK FAILED: Cannot run migration on 'buildcore'! Must run on 'buildcore_copy'.")
            return False

        try:
            with db.engine.raw_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                conn.commit()
            print(f"Successfully applied migration: '{sql_filename}' on '{curr_db}'!")
            return True
        except Exception as e:
            print(f"Migration FAILED on '{curr_db}': {e}")
            return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python run_migration.py <filename.sql>")
        sys.exit(1)
    success = apply_migration(sys.argv[1])
    sys.exit(0 if success else 1)
