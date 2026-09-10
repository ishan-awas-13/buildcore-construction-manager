import os
from sqlalchemy import text
from app import create_app, db

app = create_app()

def run_sql_file(filename):
    filepath = os.path.join(os.path.dirname(__file__), 'database', filename)
    print(f"Executing {filename}...")
    with open(filepath, 'r') as file:
        sql = file.read()
    
    with app.app_context():
        # Use raw connection to execute multi-statement SQL files reliably
        with db.engine.raw_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
    print(f"Successfully executed {filename}.")

if __name__ == "__main__":
    print("Starting database setup...")
    try:
        run_sql_file('schema.sql')
        run_sql_file('seed.sql')
        print("\nDatabase setup complete!")
        print("-" * 40)
        print("Please run the following command to create your secure admin account:")
        print("    flask create-admin")
        print("-" * 40)
    except Exception as e:
        print(f"\nError during setup: {e}")
