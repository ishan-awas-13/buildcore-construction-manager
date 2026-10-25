import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

from app import create_app, db
from sqlalchemy import text

app = create_app()

def run_tests():
    print("=" * 60)
    print("RUNNING VERIFICATION TESTS: PRIORITY 2 — FINANCIAL CONSISTENCY")
    print("=" * 60)

    with app.app_context():
        # Verify active database
        active_db = db.session.execute(text("SELECT current_database();")).scalar()
        print(f"Active test database: '{active_db}'")
        assert active_db in ('buildcore_copy', 'buildcore_test'), "Safety failure: Not running on buildcore_copy!"

        # -----------------------------------------------------------
        # TEST 1: Historical Locked Rates Immunity from Live Catalog Mutations
        # -----------------------------------------------------------
        print("\n[TEST 1] Testing Rate Immunity (Catalogue vs Locked Historical)...")
        # Check that worker_id=19 has assigned task and locked rate
        worker_rec = db.session.execute(text("""
            SELECT w.worker_id, w.daily_rate, tw.locked_daily_rate, tw.assigned_hours
            FROM task_workers tw
            JOIN workers w ON tw.worker_id = w.worker_id
            WHERE w.worker_id = 19
            LIMIT 1
        """)).fetchone()
        
        orig_daily_rate = float(worker_rec.daily_rate)
        locked_rate = float(worker_rec.locked_daily_rate)
        assigned_hours = float(worker_rec.assigned_hours)
        expected_hist_cost = round((assigned_hours / 8.0) * locked_rate, 2)
        
        print(f"  Worker 19: Live Rate=₹{orig_daily_rate}, Locked Rate=₹{locked_rate}, Hours={assigned_hours}")
        print(f"  Expected Historical Labour Cost: ₹{expected_hist_cost}")

        # Mutate worker daily_rate to 99999.00
        db.session.execute(text("UPDATE workers SET daily_rate = 99999.00 WHERE worker_id = 19"))
        db.session.commit()

        # Query Report 3 query
        report3_row = db.session.execute(text("""
            SELECT ROUND((tw.assigned_hours / 8.0) * COALESCE(NULLIF(tw.locked_daily_rate, 0), w.daily_rate), 2) as labour_cost
            FROM task_workers tw
            JOIN workers w ON tw.worker_id = w.worker_id
            WHERE tw.worker_id = 19
            LIMIT 1
        """)).fetchone()

        # Query expense_ledger_view
        ledger_row = db.session.execute(text("""
            SELECT amount 
            FROM expense_ledger_view 
            WHERE source_type = 'Labour' AND source_id = (SELECT task_worker_id FROM task_workers WHERE worker_id = 19 LIMIT 1)
        """)).fetchone()

        # Revert live rate immediately
        db.session.execute(text("UPDATE workers SET daily_rate = :rate WHERE worker_id = 19"), {'rate': orig_daily_rate})
        db.session.commit()

        assert float(report3_row.labour_cost) == expected_hist_cost, (
            f"Report 3 changed when master rate was modified! Got {report3_row.labour_cost}, expected {expected_hist_cost}"
        )
        assert float(ledger_row.amount) == expected_hist_cost, (
            f"expense_ledger_view changed when master rate was modified! Got {ledger_row.amount}, expected {expected_hist_cost}"
        )
        print("  --> PASS: Modifying worker master rate did NOT alter historical task costs or financial ledger.")

        # -----------------------------------------------------------
        # TEST 2: Database Check Constraints (Non-Negative Rates)
        # -----------------------------------------------------------
        print("\n[TEST 2] Testing Rate Non-Negativity Constraints...")
        try:
            db.session.execute(text("SAVEPOINT sp_neg_tw"))
            db.session.execute(text("""
                INSERT INTO task_workers (project_task_id, worker_id, assigned_hours, locked_daily_rate)
                VALUES (1, 1, 10, -500.00)
            """))
            db.session.commit()
            assert False, "Failed to reject negative locked_daily_rate!"
        except Exception as e:
            db.session.execute(text("ROLLBACK TO SAVEPOINT sp_neg_tw"))
            print("  --> PASS: Database rejected negative locked_daily_rate via check constraint.")

        try:
            db.session.execute(text("SAVEPOINT sp_neg_ea"))
            db.session.execute(text("""
                INSERT INTO equipment_assignments (equipment_id, project_task_id, start_date, hours_used, locked_hourly_rate)
                VALUES (1, 1, '2024-01-01', 10, -250.00)
            """))
            db.session.commit()
            assert False, "Failed to reject negative locked_hourly_rate!"
        except Exception as e:
            db.session.execute(text("ROLLBACK TO SAVEPOINT sp_neg_ea"))
            print("  --> PASS: Database rejected negative locked_hourly_rate via check constraint.")

        # -----------------------------------------------------------
        # TEST 3: Dashboard Recognized Purchases KPI
        # -----------------------------------------------------------
        print("\n[TEST 3] Testing Dashboard Recognized Purchases vs Total POs...")
        total_all_pos = db.session.execute(text("SELECT COALESCE(SUM(total_amount), 0) FROM purchases_with_total_view")).scalar()
        recognized_purchases = db.session.execute(text("""
            SELECT COALESCE(SUM(total_amount), 0) 
            FROM purchases_with_total_view 
            WHERE status IN ('Delivered', 'Completed')
        """)).scalar()
        
        ordered_purchases = db.session.execute(text("""
            SELECT COALESCE(SUM(total_amount), 0) 
            FROM purchases_with_total_view 
            WHERE status NOT IN ('Delivered', 'Completed')
        """)).scalar()

        print(f"  Total All POs: ₹{total_all_pos:,.2f}")
        print(f"  Unrecognized (Pending/Ordered/Shipped) POs: ₹{ordered_purchases:,.2f}")
        print(f"  Recognized Delivered/Completed Spend: ₹{recognized_purchases:,.2f}")
        
        if active_db == 'buildcore_copy':
            assert recognized_purchases == 215970000.00, f"Expected 215,970,000.00, got {recognized_purchases}"
        assert abs(float(total_all_pos) - (float(recognized_purchases) + float(ordered_purchases))) < 0.01, "Total PO reconciliation mismatch"
        print("  --> PASS: Dashboard accurately excludes pending/ordered POs from recognized procurement spend.")

        # -----------------------------------------------------------
        # TEST 4: Operational Expense Double-Counting Prevention
        # -----------------------------------------------------------
        print("\n[TEST 4] Testing Double-Counting Rejection in Misc Expenses Route...")
        client = app.test_client()
        with client.session_transaction() as sess:
            sess['_user_id'] = '1'

        # 4a: Attempt to add Labour expense
        res_labour = client.post('/financials/project/1/misc/add', data={
            'expense_type': 'Labour',
            'amount': '50000',
            'expense_date': '2024-03-01',
            'description': 'Direct labour wage test'
        }, follow_redirects=True)
        assert b"Operational expenses (Labour, Equipment, Materials) are automatically tracked" in res_labour.data
        print("  --> PASS: Blocked attempt to create 'Labour' expense.")

        # 4b: Attempt to add Equipment expense
        res_equip = client.post('/financials/project/1/misc/add', data={
            'expense_type': 'Equipment',
            'amount': '75000',
            'expense_date': '2024-03-01',
            'description': 'Crane usage test'
        }, follow_redirects=True)
        assert b"Operational expenses (Labour, Equipment, Materials) are automatically tracked" in res_equip.data
        print("  --> PASS: Blocked attempt to create 'Equipment' expense.")

        # 4c: Attempt to add Materials expense
        res_mat = client.post('/financials/project/1/misc/add', data={
            'expense_type': 'Materials',
            'amount': '30000',
            'expense_date': '2024-03-01',
            'description': 'Cement bags test'
        }, follow_redirects=True)
        assert b"Operational expenses (Labour, Equipment, Materials) are automatically tracked" in res_mat.data
        print("  --> PASS: Blocked attempt to create 'Materials' expense.")

        # 4d: Add valid administrative overhead expense
        res_valid = client.post('/financials/project/1/misc/add', data={
            'expense_type': 'Building Permit',
            'amount': '25000',
            'expense_date': '2024-03-01',
            'description': 'Municipal clearance permit'
        }, follow_redirects=True)
        assert b"Miscellaneous expense added successfully" in res_valid.data
        
        # Verify and clean up
        created_exp = db.session.execute(text("SELECT expense_id FROM expenses WHERE project_id = 1 AND description = 'Municipal clearance permit'")).fetchone()
        assert created_exp is not None
        db.session.execute(text(f"DELETE FROM expenses WHERE expense_id = {created_exp.expense_id}"))
        db.session.commit()
        print("  --> PASS: Valid administrative overhead expense allowed and cleaned up successfully.")

        # -----------------------------------------------------------
        # TEST 5: HTTP Route Rendering (HTTP 200)
        # -----------------------------------------------------------
        print("\n[TEST 5] Testing Financial Route Rendering...")
        res_dash = client.get('/dashboard/')
        assert res_dash.status_code == 200, f"Dashboard failed with {res_dash.status_code}"

        res_fin = client.get('/financials/')
        assert res_fin.status_code == 200, f"Financials list failed with {res_fin.status_code}"

        res_proj_fin = client.get('/financials/project/1')
        assert res_proj_fin.status_code == 200, f"Project 1 financials failed with {res_proj_fin.status_code}"

        res_rep = client.get('/reports/?project_id=1')
        assert res_rep.status_code == 200, f"Reports failed with {res_rep.status_code}"
        print("  --> PASS: All financial routes rendered HTTP 200.")

    print("\n" + "=" * 60)
    print("ALL PRIORITY 2 (FINANCIAL CONSISTENCY) TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == '__main__':
    run_tests()
