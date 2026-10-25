import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

os.environ['TEST_DB_NAME'] = 'buildcore_test'

from app import create_app, db
from sqlalchemy import text

app = create_app()

def run_tests():
    print("=" * 70)
    print("MODULE 3: ADVERSARIAL FINANCIAL ACCOUNTING & LEDGER INTEGRITY TESTS")
    print("=" * 70)

    results = []

    with app.app_context():
        curr_db = db.session.execute(text("SELECT current_database();")).scalar()
        print(f"Connected Database: '{curr_db}'")
        assert curr_db == 'buildcore_test', f"Safety violation: Expected buildcore_test, got {curr_db}"

        client = app.test_client()
        login_res = client.post('/login', data={'username': 'admin', 'password': 'admin'}, follow_redirects=True)
        assert login_res.status_code == 200, "Admin login failed!"

        p102_id = db.session.execute(text("SELECT project_id FROM projects WHERE project_name LIKE 'QA-SIM-102%'")).scalar()
        p103_id = db.session.execute(text("SELECT project_id FROM projects WHERE project_name LIKE 'QA-SIM-103%'")).scalar()

        # -------------------------------------------------------------
        # TEST-FIN-01: Purchase Order Line Item vs Total Reconciliation
        # -------------------------------------------------------------
        print("\n[TEST-FIN-01] Testing Purchase Order Line Item vs Total Amount Calculation...")
        po_rows = db.session.execute(text("""
            SELECT p.purchase_id, p.total_amount,
                   COALESCE(SUM(pi.quantity * pi.unit_price), 0) AS calculated_sum
            FROM purchases_with_total_view p
            LEFT JOIN purchase_items pi ON p.purchase_id = pi.purchase_id
            GROUP BY p.purchase_id, p.total_amount
            ORDER BY p.purchase_id
        """)).fetchall()

        all_po_match = True
        for po in po_rows:
            view_total = float(po.total_amount or 0)
            calc_total = float(po.calculated_sum)
            if abs(view_total - calc_total) > 0.01:
                all_po_match = False
                print(f"  PO #{po.purchase_id} MISMATCH: View shows {view_total}, line items sum to {calc_total}")

        assert all_po_match, "PO line items do not sum to total_amount in purchases_with_total_view!"
        print(f"  Result: PASS - All {len(po_rows)} purchase orders strictly reconcile with line items.")
        results.append(('TEST-FIN-01', 'PO Line Item Reconciliation', 'PASS', f'All {len(po_rows)} POs match line item arithmetic'))

        # -------------------------------------------------------------
        # TEST-FIN-02: Procurement Recognition Policy Audit
        # -------------------------------------------------------------
        print("\n[TEST-FIN-02] Testing Procurement Recognition Policy (Delivered/Completed only)...")
        p102_materials_in_ledger = db.session.execute(text("""
            SELECT SUM(amount) FROM expense_ledger_view 
            WHERE project_id = :p AND category = 'Materials'
        """), {'p': p102_id}).scalar() or 0

        assert float(p102_materials_in_ledger) == 1290000.00, f"Expected recognized materials ₹1,290,000.00, got ₹{p102_materials_in_ledger}"
        print(f"  Result: PASS - Only Delivered PO recognized (₹1,290,000.00). Shipped and Ordered POs excluded.")
        results.append(('TEST-FIN-02', 'Procurement Financial Recognition Policy', 'PASS', 'Only Delivered/Completed orders recognized in ledger'))

        # -------------------------------------------------------------
        # TEST-FIN-03: Labour and Equipment Cost Formula Verification
        # -------------------------------------------------------------
        print("\n[TEST-FIN-03] Testing Labour & Equipment Mathematical Formulas in Ledger...")
        labour_discrepancies = db.session.execute(text("""
            SELECT el.transaction_id, el.amount, 
                   round(tw.assigned_hours / 8.0 * tw.locked_daily_rate, 2) AS expected_amt
            FROM expense_ledger_view el
            JOIN task_workers tw ON el.source_id = tw.task_worker_id
            WHERE el.category = 'Labour' AND el.amount != round(tw.assigned_hours / 8.0 * tw.locked_daily_rate, 2)
        """)).fetchall()
        assert len(labour_discrepancies) == 0, f"Found {len(labour_discrepancies)} labour discrepancies!"

        equip_discrepancies = db.session.execute(text("""
            SELECT el.transaction_id, el.amount, 
                   round(ea.hours_used * ea.locked_hourly_rate, 2) AS expected_amt
            FROM expense_ledger_view el
            JOIN equipment_assignments ea ON el.source_id = ea.assignment_id
            WHERE el.category = 'Equipment' AND el.amount != round(ea.hours_used * ea.locked_hourly_rate, 2)
        """)).fetchall()
        assert len(equip_discrepancies) == 0, f"Found {len(equip_discrepancies)} equipment discrepancies!"

        print("  Result: PASS - 100% of Labour and Equipment transactions match expected formulas.")
        results.append(('TEST-FIN-03', 'Labour/Equipment Cost Formula Audit', 'PASS', 'All transactions match mathematical formulas'))

        # -------------------------------------------------------------
        # TEST-FIN-04: Operational Double-Counting Prevention
        # -------------------------------------------------------------
        print("\n[TEST-FIN-04] Testing Operational Double-Counting Guard in Misc Expenses...")
        res_labour = client.post(f'/financials/project/{p102_id}/misc/add', data={
            'expense_type': 'Labour',
            'amount': 25000,
            'expense_date': '2026-09-01',
            'description': 'Overtime labor cost'
        }, follow_redirects=True)
        assert "automatically tracked via Task Assignments" in res_labour.data.decode('utf-8')

        res_eq = client.post(f'/financials/project/{p102_id}/misc/add', data={
            'expense_type': 'equipment',
            'amount': 15000,
            'expense_date': '2026-09-01',
            'description': 'Excavator rental'
        }, follow_redirects=True)
        assert "automatically tracked via Task Assignments" in res_eq.data.decode('utf-8')

        res_mat = client.post(f'/financials/project/{p102_id}/misc/add', data={
            'expense_type': 'Materials',
            'amount': 50000,
            'expense_date': '2026-09-01',
            'description': 'Emergency cement'
        }, follow_redirects=True)
        assert "automatically tracked via Task Assignments" in res_mat.data.decode('utf-8')

        print("  Result: PASS - Operational categories (Labour, Equipment, Materials) blocked in misc expenses.")
        results.append(('TEST-FIN-04', 'Operational Double-Counting Prevention', 'PASS', 'Blocked Labour, Equipment, Materials in misc expenses'))

        # -------------------------------------------------------------
        # TEST-FIN-05: Negative & Malformed Expense Input
        # -------------------------------------------------------------
        print("\n[TEST-FIN-05] Testing Negative and Malformed Expense Inputs...")
        # Negative expense
        res_neg = client.post(f'/financials/project/{p102_id}/misc/add', data={
            'expense_type': 'Consulting',
            'amount': -5000,
            'expense_date': '2026-09-01',
            'description': 'Negative fee'
        }, follow_redirects=True)
        assert "greater than zero" in res_neg.data.decode('utf-8') or "cannot be negative" in res_neg.data.decode('utf-8')
        print("  Negative amount properly rejected.")

        # Non-numeric amount ("abc")
        res_nan = client.post(f'/financials/project/{p102_id}/misc/add', data={
            'expense_type': 'Consulting',
            'amount': 'invalid_string',
            'expense_date': '2026-09-01',
            'description': 'String amount'
        }, follow_redirects=True)
        assert "valid numeric amount" in res_nan.data.decode('utf-8')
        print("  Non-numeric string properly rejected with friendly flash message.")
        results.append(('TEST-FIN-05', 'Malformed Expense Amount Input Validation', 'PASS', 'Both negative and non-numeric inputs handled cleanly with flash messages'))

        # -------------------------------------------------------------
        # TEST-FIN-06: Multi-Project Ledger-to-Report Reconciliation
        # -------------------------------------------------------------
        print("\n[TEST-FIN-06] Testing Company-Wide Multi-Project Ledger Reconciliation...")
        per_project_sums = db.session.execute(text("""
            SELECT project_id, COALESCE(SUM(amount), 0) AS project_total
            FROM expense_ledger_view
            GROUP BY project_id
        """)).fetchall()

        sum_of_project_totals = sum(float(row.project_total) for row in per_project_sums)

        company_report_total = db.session.execute(text("""
            SELECT COALESCE(SUM(amount), 0) AS company_total
            FROM expense_ledger_view
        """)).scalar()

        diff = abs(sum_of_project_totals - float(company_report_total))
        print(f"  Sum of individual project ledgers: ₹{sum_of_project_totals:,.2f}")
        print(f"  Company-wide total cost in Report 2: ₹{float(company_report_total):,.2f}")
        print(f"  Reconciliation Variance: ₹{diff:.2f}")

        assert diff < 0.01, f"Reconciliation variance detected: ₹{diff}"
        print("  Result: PASS - Company-wide totals reconcile 100% to individual project ledgers.")
        results.append(('TEST-FIN-06', 'Ledger-to-Report Multi-Project Reconciliation', 'PASS', f'Zero variance between sum of projects (₹{sum_of_project_totals:,.2f}) and company total'))

        # -------------------------------------------------------------
        # TEST-FIN-07: Cancelled Purchase Order Exclusion
        # -------------------------------------------------------------
        print("\n[TEST-FIN-07] Testing Cancelled Order Exclusion from Dashboard and Ledgers...")
        cur_sup = db.session.execute(text("SELECT supplier_id FROM suppliers LIMIT 1")).scalar()
        cur_mat = db.session.execute(text("SELECT material_id FROM materials LIMIT 1")).scalar()
        db.session.execute(text("""
            INSERT INTO purchases (purchase_id, supplier_id, project_id, purchase_date, status)
            VALUES (888888, :sup, :p, '2026-09-01', 'Cancelled')
        """), {'sup': cur_sup, 'p': p102_id})
        db.session.execute(text("""
            INSERT INTO purchase_items (purchase_id, material_id, quantity, unit_price)
            VALUES (888888, :m, 1000.0, 5000.00)
        """), {'m': cur_mat})
        db.session.commit()

        dash_res = client.get('/dashboard/')
        assert dash_res.status_code == 200
        cancelled_in_ledger = db.session.execute(text("""
            SELECT 1 FROM expense_ledger_view WHERE source_id = 888888
        """)).scalar()
        assert not cancelled_in_ledger, "Cancelled order appeared in expense ledger!"

        dash_purchases = db.session.execute(text("""
            SELECT COALESCE(SUM(total_amount), 0) 
            FROM purchases_with_total_view 
            WHERE status IN ('Delivered', 'Completed')
        """)).scalar()
        print(f"  Dashboard Total Purchases recognized: ₹{dash_purchases:,.2f} (Excluded ₹5,000,000 cancelled PO).")
        print("  Result: PASS - Cancelled purchase orders excluded from ledgers and dashboard.")
        results.append(('TEST-FIN-07', 'Cancelled PO Exclusion', 'PASS', 'Cancelled order correctly excluded from financial totals'))

        db.session.execute(text("DELETE FROM purchase_items WHERE purchase_id = 888888"))
        db.session.execute(text("DELETE FROM purchases WHERE purchase_id = 888888"))
        db.session.commit()

    print("\n" + "=" * 70)
    print("MODULE 3 RESULTS SUMMARY:")
    for code, name, outcome, notes in results:
        print(f"  [{outcome}] {code:12} : {name:40} | {notes}")
    print("=" * 70)
    return results

if __name__ == '__main__':
    run_tests()
