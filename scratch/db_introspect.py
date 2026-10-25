import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

from app import create_app, db
from sqlalchemy import text

app = create_app()

def inspect():
    with app.app_context():
        # Check connection
        print("Connected to DB successfully.")
        
        # 1. List all tables
        tables = db.session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)).fetchall()
        print("\n=== BASE TABLES ===")
        for t in tables:
            print(f"- {t[0]}")
            
        # 2. List all views
        views = db.session.execute(text("""
            SELECT table_name 
            FROM information_schema.views 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)).fetchall()
        print("\n=== VIEWS ===")
        for v in views:
            print(f"- {v[0]}")
            
        # 3. View definition of expense_ledger_view, worker_status_view, equipment_status_view
        for v in ['expense_ledger_view', 'worker_status_view', 'equipment_status_view', 'project_progress_view', 'purchases_with_total_view']:
            view_def = db.session.execute(text(f"""
                SELECT view_definition 
                FROM information_schema.views 
                WHERE table_name = '{v}'
            """)).fetchone()
            if view_def:
                print(f"\n--- VIEW DEFINITION: {v} ---")
                print(view_def[0])
                
        # 4. Check row counts in tables
        print("\n=== ROW COUNTS ===")
        for t in tables:
            cnt = db.session.execute(text(f"SELECT COUNT(*) FROM {t[0]}")).scalar()
            print(f"{t[0]}: {cnt} rows")

        # 5. Check task_workers locked rates vs daily rates
        print("\n=== TASK WORKERS SAMPLE ===")
        tw = db.session.execute(text("""
            SELECT tw.task_worker_id, tw.assigned_hours, tw.locked_daily_rate, w.daily_rate
            FROM task_workers tw
            JOIN workers w ON tw.worker_id = w.worker_id
            LIMIT 5
        """)).fetchall()
        for r in tw:
            print(f"TW {r[0]}: assigned_hours={r[1]}, locked_daily_rate={r[2]}, worker.daily_rate={r[3]}")

        # 6. Check equipment_assignments locked rates vs hourly rates
        print("\n=== EQUIPMENT ASSIGNMENTS SAMPLE ===")
        ea = db.session.execute(text("""
            SELECT ea.assignment_id, ea.hours_used, ea.locked_hourly_rate, e.hourly_rate
            FROM equipment_assignments ea
            JOIN equipment e ON ea.equipment_id = e.equipment_id
            LIMIT 5
        """)).fetchall()
        for r in ea:
            print(f"EA {r[0]}: hours_used={r[1]}, locked_hourly_rate={r[2]}, eq.hourly_rate={r[3]}")

        # 7. Check expenses table categories/types
        print("\n=== EXPENSES TYPES ===")
        exp = db.session.execute(text("""
            SELECT expense_type, COUNT(*), SUM(amount)
            FROM expenses
            GROUP BY expense_type
        """)).fetchall()
        for r in exp:
            print(f"Expense type '{r[0]}': {r[1]} rows, total={r[2]}")

        # 8. Check materials table columns
        cols = db.session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'materials'
        """)).fetchall()
        print("\n=== MATERIALS COLUMNS ===")
        for c in cols:
            print(f"- {c[0]}: {c[1]}")

        # 9. Check constraints
        print("\n=== CONSTRAINTS ===")
        constraints = db.session.execute(text("""
            SELECT conrelid::regclass::text as table_name, conname, contype, pg_get_constraintdef(oid) as def
            FROM pg_constraint
            WHERE connamespace = 'public'::regnamespace
            ORDER BY conrelid::regclass::text, conname
        """)).fetchall()
        for c in constraints:
            print(f"[{c.table_name}] {c.conname} ({c.contype}): {getattr(c, 'def')}")

        # 10. Check project_workers table usage vs task_workers
        print("\n=== PROJECT_WORKERS vs TASK_WORKERS ===")
        pw_cnt = db.session.execute(text("SELECT count(*) FROM project_workers")).scalar()
        tw_cnt = db.session.execute(text("SELECT count(*) FROM task_workers")).scalar()
        print(f"project_workers count: {pw_cnt}, task_workers count: {tw_cnt}")

        # 11. Check material_usage table data
        print("\n=== MATERIAL USAGE ROWS ===")
        mu_rows = db.session.execute(text("""
            SELECT mu.usage_id, mu.project_id, p.project_name, mu.material_id, m.material_name,
                   mu.quantity_allocated, mu.quantity_used
            FROM material_usage mu
            JOIN projects p ON mu.project_id = p.project_id
            JOIN materials m ON mu.material_id = m.material_id
            ORDER BY mu.project_id, mu.material_id
        """)).fetchall()
        for r in mu_rows:
            print(f"Usage {r.usage_id}: Project '{r.project_name}' (ID {r.project_id}) - {r.material_name}: alloc={r.quantity_allocated}, used={r.quantity_used}")

        # 12. Check purchases per project vs material_usage per project
        print("\n=== PURCHASES vs MATERIAL USAGE PER PROJECT ===")
        purch_rows = db.session.execute(text("""
            SELECT p.project_id, pr.project_name, pi.material_id, m.material_name,
                   p.status as purchase_status, SUM(pi.quantity) as purchased_qty
            FROM purchase_items pi
            JOIN purchases p ON pi.purchase_id = p.purchase_id
            JOIN projects pr ON p.project_id = pr.project_id
            JOIN materials m ON pi.material_id = m.material_id
            GROUP BY p.project_id, pr.project_name, pi.material_id, m.material_name, p.status
            ORDER BY p.project_id, pi.material_id
        """)).fetchall()
        for r in purch_rows:
            print(f"Purchase: Project '{r.project_name}' (ID {r.project_id}) - {r.material_name}: status={r.purchase_status}, qty={r.purchased_qty}")

        # 13. Check for any task without project or worker without task
        print("\n=== WORKER ASSIGNMENT DATES & CONFLICTS ===")
        worker_conflicts = db.session.execute(text("""
            SELECT tw1.worker_id, w.name, tw1.project_task_id as pt1, pt1.start_date as s1, pt1.due_date as d1,
                   tw2.project_task_id as pt2, pt2.start_date as s2, pt2.due_date as d2
            FROM task_workers tw1
            JOIN task_workers tw2 ON tw1.worker_id = tw2.worker_id AND tw1.task_worker_id < tw2.task_worker_id
            JOIN project_tasks pt1 ON tw1.project_task_id = pt1.project_task_id
            JOIN project_tasks pt2 ON tw2.project_task_id = pt2.project_task_id
            JOIN workers w ON tw1.worker_id = w.worker_id
            WHERE pt1.start_date <= pt2.due_date AND pt1.due_date >= pt2.start_date
        """)).fetchall()
        print(f"Worker overlapping task assignments count: {len(worker_conflicts)}")
        for wc in worker_conflicts:
            print(f"Worker {wc.name} assigned to task {wc.pt1} ({wc.s1} to {wc.d1}) AND task {wc.pt2} ({wc.s2} to {wc.d2})")

        # 14. Check task completion percentage vs status contradictions
        print("\n=== TASK STATUS VS COMPLETION PERCENTAGE ===")
        task_contra = db.session.execute(text("""
            SELECT project_task_id, project_id, status, completion_percentage
            FROM project_tasks
            WHERE (status = 'Completed' AND completion_percentage < 100)
               OR (status != 'Completed' AND completion_percentage = 100)
               OR (status = 'Not Started' AND completion_percentage > 0)
        """)).fetchall()
        print(f"Tasks with status/percentage contradictions: {len(task_contra)}")
        for tc in task_contra:
            print(f"Task {tc.project_task_id} (Project {tc.project_id}): status='{tc.status}', pct={tc.completion_percentage}")

if __name__ == '__main__':
    inspect()

