import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ['TEST_DB_NAME'] = 'buildcore_test'

from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    curr_db = db.session.execute(text("SELECT current_database();")).scalar()
    print(f"Connected to database: {curr_db}")
    assert curr_db == 'buildcore_test', f"Safety violation: Expected buildcore_test, got {curr_db}"

    print("Cleaning up synthetic records with ID thresholds...")
    db.session.execute(text("DELETE FROM expenses WHERE expense_id >= 6000"))
    db.session.execute(text("DELETE FROM purchase_items WHERE purchase_item_id >= 5000"))
    db.session.execute(text("DELETE FROM purchases WHERE purchase_id >= 4000"))
    db.session.execute(text("DELETE FROM task_workers WHERE task_worker_id >= 3000"))
    db.session.execute(text("DELETE FROM workers WHERE worker_id >= 1000"))
    db.session.execute(text("DELETE FROM project_tasks WHERE project_task_id >= 2000"))
    db.session.execute(text("DELETE FROM projects WHERE project_id >= 1000"))
    db.session.commit()
    print("Purge completed successfully.")
