import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app, db
from sqlalchemy import text

app = create_app()

def run_migration():
    with app.app_context():
        try:
            print("Applying Database Hardening Migration...")
            
            # 1. Update material_usage constraint
            print("Adding check constraint to material_usage (quantity_used <= quantity_allocated)...")
            # First remove if it exists to make it idempotent
            db.session.execute(text("ALTER TABLE material_usage DROP CONSTRAINT IF EXISTS check_material_used"))
            db.session.execute(text("ALTER TABLE material_usage ADD CONSTRAINT check_material_used CHECK (quantity_used <= quantity_allocated)"))
            
            # 2. Update expense_ledger_view safely
            print("Updating expense_ledger_view to filter purchase status and round materials amount...")
            
            view_sql = text("""
            CREATE OR REPLACE VIEW expense_ledger_view AS
            -- MATERIALS: Cost comes from actual purchase line items
            SELECT
                'MAT-' || pi.purchase_item_id AS transaction_id,
                p.project_id,
                p.purchase_date AS transaction_date,
                'Materials' AS category,
                m.material_name || ' — ' || pi.quantity || ' ' || m.unit || ' @ ₹' || pi.unit_price AS description,
                ROUND(pi.quantity * pi.unit_price, 2) AS amount,
                'Purchase' AS source_type,
                p.purchase_id AS source_id
            FROM purchase_items pi
            JOIN purchases p ON pi.purchase_id = p.purchase_id
            JOIN materials m ON pi.material_id = m.material_id
            WHERE p.status IN ('Delivered', 'Completed')

            UNION ALL

            -- LABOUR: Cost = (assigned_hours / 8) * daily_rate
            SELECT
                'LAB-' || tw.task_worker_id AS transaction_id,
                pt.project_id,
                pt.start_date AS transaction_date,
                'Labour' AS category,
                w.name || ' — ' || tt.task_name || ' (' || tw.assigned_hours || ' hrs)' AS description,
                ROUND((tw.assigned_hours / 8.0) * w.daily_rate, 2) AS amount,
                'Labour' AS source_type,
                tw.task_worker_id AS source_id
            FROM task_workers tw
            JOIN workers w ON tw.worker_id = w.worker_id
            JOIN project_tasks pt ON tw.project_task_id = pt.project_task_id
            JOIN task_types tt ON pt.task_type_id = tt.task_type_id

            UNION ALL

            -- EQUIPMENT: Cost = hours_used * hourly_rate
            SELECT
                'EQP-' || ea.assignment_id AS transaction_id,
                pt.project_id,
                ea.start_date AS transaction_date,
                'Equipment' AS category,
                eq.equipment_name || ' — ' || tt.task_name || ' (' || ea.hours_used || ' hrs)' AS description,
                ROUND(ea.hours_used * eq.hourly_rate, 2) AS amount,
                'Equipment' AS source_type,
                ea.assignment_id AS source_id
            FROM equipment_assignments ea
            JOIN equipment eq ON ea.equipment_id = eq.equipment_id
            JOIN project_tasks pt ON ea.project_task_id = pt.project_task_id
            JOIN task_types tt ON pt.task_type_id = tt.task_type_id

            UNION ALL

            -- OTHER / MISCELLANEOUS: Direct from expenses table
            SELECT
                'MISC-' || e.expense_id AS transaction_id,
                e.project_id,
                e.expense_date AS transaction_date,
                'Other' AS category,
                e.expense_type || ' — ' || COALESCE(e.description, '') AS description,
                e.amount,
                'Misc Expense' AS source_type,
                e.expense_id AS source_id
            FROM expenses e;
            """)
            db.session.execute(view_sql)
            
            db.session.commit()
            print("Migration applied successfully! Validating...")
            
            # Verify totals
            sys.stdout.reconfigure(encoding='utf-8')
            res = db.session.execute(text('SELECT category, COUNT(*), SUM(amount) FROM expense_ledger_view GROUP BY category')).fetchall()
            for r in res:
                print(f"{r[0]}: {r[1]} entries, total Rs.{r[2]}")
                
        except Exception as e:
            db.session.rollback()
            print(f"Error during migration: {e}")

if __name__ == '__main__':
    run_migration()
