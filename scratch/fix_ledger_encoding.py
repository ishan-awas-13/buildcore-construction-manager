import sys
import psycopg2

sys.stdout.reconfigure(encoding='utf-8')

databases = ['buildcore_copy', 'buildcore_test']

view_sql = """
CREATE OR REPLACE VIEW expense_ledger_view AS

-- MATERIALS: Cost comes from actual purchase line items
SELECT
    'MAT-' || pi.purchase_item_id AS transaction_id,
    p.project_id,
    p.purchase_date AS transaction_date,
    'Materials' AS category,
    m.material_name || ' - ' || pi.quantity || ' ' || m.unit || ' @ ₹' || pi.unit_price AS description,
    ROUND(pi.quantity * pi.unit_price, 2) AS amount,
    'Purchase' AS source_type,
    p.purchase_id AS source_id
FROM purchase_items pi
JOIN purchases p ON pi.purchase_id = p.purchase_id
JOIN materials m ON pi.material_id = m.material_id
WHERE p.status IN ('Delivered', 'Completed')

UNION ALL

-- LABOUR: Cost = (assigned_hours / 8) * locked_daily_rate
SELECT
    'LAB-' || tw.task_worker_id AS transaction_id,
    pt.project_id,
    pt.start_date AS transaction_date,
    'Labour' AS category,
    w.name || ' - ' || tt.task_name || ' (' || tw.assigned_hours || ' hrs)' AS description,
    ROUND((tw.assigned_hours / 8.0) * tw.locked_daily_rate, 2) AS amount,
    'Labour' AS source_type,
    tw.task_worker_id AS source_id
FROM task_workers tw
JOIN workers w ON tw.worker_id = w.worker_id
JOIN project_tasks pt ON tw.project_task_id = pt.project_task_id
JOIN task_types tt ON pt.task_type_id = tt.task_type_id

UNION ALL

-- EQUIPMENT: Cost = hours_used * locked_hourly_rate
SELECT
    'EQP-' || ea.assignment_id AS transaction_id,
    pt.project_id,
    ea.start_date AS transaction_date,
    'Equipment' AS category,
    eq.equipment_name || ' - ' || tt.task_name || ' (' || ea.hours_used || ' hrs)' AS description,
    ROUND(ea.hours_used * ea.locked_hourly_rate, 2) AS amount,
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
    e.expense_type || ' - ' || COALESCE(e.description, '') AS description,
    e.amount,
    'Misc Expense' AS source_type,
    e.expense_id AS source_id
FROM expenses e;
"""

for dbname in databases:
    conn = psycopg2.connect(f'postgresql://postgres:admin123@localhost:5432/{dbname}')
    conn.set_client_encoding('UTF8')
    cur = conn.cursor()
    cur.execute(view_sql)
    conn.commit()
    
    # Query project 6 descriptions to verify
    cur.execute("SELECT description FROM expense_ledger_view WHERE project_id = 6 LIMIT 5")
    rows = cur.fetchall()
    print(f"\n--- {dbname} Sample Descriptions ---")
    for r in rows:
        print(" ", r[0])
    conn.close()

print("\nSuccessfully updated expense_ledger_view across all databases!")
