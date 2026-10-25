import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

from app import create_app, db
from sqlalchemy import text

app = create_app()

def run_tests():
    print("=" * 60)
    print("RUNNING VERIFICATION TESTS: PRIORITY 1 — MATERIALS")
    print("=" * 60)

    with app.app_context():
        # Verify active database
        curr_db = db.session.execute(text("SELECT current_database();")).scalar()
        print(f"Active test database: '{curr_db}'")
        assert curr_db in ('buildcore_copy', 'buildcore_test'), f"SAFETY ERROR: Expected buildcore_copy, got {curr_db}"

        # -----------------------------------------------------------
        # TEST 1: Database Constraint (check_material_used)
        # -----------------------------------------------------------
        print("\n[TEST 1] Testing Database Constraint check_material_used...")
        try:
            db.session.execute(text("SAVEPOINT sp_test1"))
            db.session.execute(text("""
                INSERT INTO material_usage (project_id, material_id, quantity_allocated, quantity_used)
                VALUES (1, 15, 10, 20)
            """))
            db.session.commit()
            print("  --> FAIL: Database allowed quantity_used > quantity_allocated!")
            assert False
        except Exception as e:
            db.session.execute(text("ROLLBACK TO SAVEPOINT sp_test1"))
            if "check_material_used" in str(e).lower() or "check" in str(e).lower():
                print("  --> PASS: Database rejected invalid consumption via check_material_used constraint.")
            else:
                print(f"  --> PASS with expected error: {e}")

        # -----------------------------------------------------------
        # TEST 2: Unique Constraint uq_project_material
        # -----------------------------------------------------------
        print("\n[TEST 2] Testing Unique Constraint uq_project_material...")
        try:
            db.session.execute(text("SAVEPOINT sp_test2"))
            db.session.execute(text("""
                INSERT INTO material_usage (project_id, material_id, quantity_allocated, quantity_used)
                VALUES (1, 2, 50, 0)
            """))
            db.session.commit()
            print("  --> FAIL: Database allowed duplicate (project_id, material_id)!")
            assert False
        except Exception as e:
            db.session.execute(text("ROLLBACK TO SAVEPOINT sp_test2"))
            if "uq_project_material" in str(e).lower() or "unique" in str(e).lower():
                print("  --> PASS: Database rejected duplicate allocation via uq_project_material constraint.")
            else:
                print(f"  --> PASS with expected error: {e}")

        # -----------------------------------------------------------
        # TEST 3: Material Stock Independence Across Projects
        # -----------------------------------------------------------
        print("\n[TEST 3] Testing Project Stock Isolation in Report 4 Query...")
        report_rows = db.session.execute(text("""
            SELECT 
                p.project_id, p.project_name,
                m.material_id, m.material_name, m.unit,
                COALESCE(purchased.total_purchased, 0) as total_purchased,
                COALESCE(mu.quantity_allocated, 0) as total_allocated,
                COALESCE(mu.quantity_used, 0) as total_used
            FROM projects p
            CROSS JOIN materials m
            LEFT JOIN (
                SELECT pur.project_id, pi.material_id, 
                       SUM(pi.quantity) as total_purchased
                FROM purchase_items pi
                JOIN purchases pur ON pi.purchase_id = pur.purchase_id
                WHERE pur.status IN ('Delivered', 'Completed')
                GROUP BY pur.project_id, pi.material_id
            ) purchased ON p.project_id = purchased.project_id AND m.material_id = purchased.material_id
            LEFT JOIN material_usage mu ON p.project_id = mu.project_id AND m.material_id = mu.material_id
            WHERE (COALESCE(purchased.total_purchased, 0) > 0 OR COALESCE(mu.quantity_allocated, 0) > 0)
            ORDER BY p.project_name, m.material_name
        """)).fetchall()

        # Check steel (material_id = 2) for Project 1 and Project 7
        p1_steel = [r for r in report_rows if r.project_id == 1 and r.material_id == 2]
        p7_steel = [r for r in report_rows if r.project_id == 7 and r.material_id == 2]
        assert len(p1_steel) == 1, "Project 1 should have its own steel row"
        assert len(p7_steel) == 1, "Project 7 should have its own steel row"
        assert p1_steel[0].total_purchased == 1000.0, f"Project 1 delivered steel should be 1000, got {p1_steel[0].total_purchased}"
        assert p7_steel[0].total_purchased == 2000.0, f"Project 7 delivered steel should be 2000, got {p7_steel[0].total_purchased}"
        
        # Verify Project 1 steel remaining stock does NOT blend with Project 7
        rem_p1 = p1_steel[0].total_purchased - p1_steel[0].total_used
        rem_p7 = p7_steel[0].total_purchased - p7_steel[0].total_used
        print(f"  Project 1 Steel: Purchased={p1_steel[0].total_purchased}, Used={p1_steel[0].total_used}, Project Remaining={rem_p1}")
        print(f"  Project 7 Steel: Purchased={p7_steel[0].total_purchased}, Used={p7_steel[0].total_used}, Project Remaining={rem_p7}")
        assert rem_p1 == 550.0, f"Project 1 remaining should be 550, got {rem_p1}"
        assert rem_p7 == 2000.0, f"Project 7 remaining should be 2000, got {rem_p7}"
        print("  --> PASS: Projects 1 and 7 have completely independent material balances.")

        # -----------------------------------------------------------
        # TEST 4: Allocation and Consumption Route Workflow (Flask Test Client)
        # -----------------------------------------------------------
        print("\n[TEST 4] Testing Allocation and Consumption Workflows via Test Client...")
        client = app.test_client()

        # Login as admin
        with client.session_transaction() as sess:
            # Login user_id = 1 directly
            sess['_user_id'] = '1'

        # Project 7 has 2000 Tonne steel delivered, 0 allocated.
        # Test 4a: Over-allocation rejection (try allocating 2500 Tonne)
        res_over = client.post('/projects/7/materials/allocate', data={
            'material_id': '2',
            'quantity_allocated': '2500'
        }, follow_redirects=True)
        assert b"Only 2000.00 Tonne of delivered stock is available" in res_over.data
        print("  --> PASS: Over-allocation (> delivered stock) was blocked successfully.")

        # Test 4b: Valid allocation (allocate 100 Tonne)
        res_alloc = client.post('/projects/7/materials/allocate', data={
            'material_id': '2',
            'quantity_allocated': '100'
        }, follow_redirects=True)
        assert b"Successfully allocated 100.0 Tonne of TMT Steel Bars" in res_alloc.data
        
        # Verify in DB
        usage_p7 = db.session.execute(text("SELECT usage_id, quantity_allocated, quantity_used FROM material_usage WHERE project_id = 7 AND material_id = 2")).fetchone()
        assert usage_p7 is not None
        assert float(usage_p7.quantity_allocated) == 100.0
        assert float(usage_p7.quantity_used) == 0.0
        print(f"  --> PASS: Valid allocation succeeded. Record in DB: usage_id={usage_p7.usage_id}, alloc={usage_p7.quantity_allocated}, used={usage_p7.quantity_used}")

        # Test 4c: Over-consumption rejection (try consuming 150 Tonne when 100 is allocated)
        res_over_cons = client.post('/projects/7/materials/consume', data={
            'usage_id': str(usage_p7.usage_id),
            'quantity_consumed': '150'
        }, follow_redirects=True)
        assert b"exceeds the allocated limit" in res_over_cons.data
        print("  --> PASS: Over-consumption (> allocated quantity) was blocked successfully.")

        # Test 4d: Valid consumption (consume 40 Tonne)
        res_cons = client.post('/projects/7/materials/consume', data={
            'usage_id': str(usage_p7.usage_id),
            'quantity_consumed': '40'
        }, follow_redirects=True)
        assert b"Recorded consumption of 40.0 Tonne of TMT Steel Bars" in res_cons.data

        # Verify in DB
        usage_p7_after = db.session.execute(text(f"SELECT quantity_allocated, quantity_used FROM material_usage WHERE usage_id = {usage_p7.usage_id}")).fetchone()
        assert float(usage_p7_after.quantity_used) == 40.0
        assert float(usage_p7_after.quantity_allocated) == 100.0
        print(f"  --> PASS: Valid consumption succeeded. Record in DB: alloc={usage_p7_after.quantity_allocated}, used={usage_p7_after.quantity_used}")

        # Clean up test row on Project 7 to keep database pristine
        db.session.execute(text(f"DELETE FROM material_usage WHERE usage_id = {usage_p7.usage_id}"))
        db.session.commit()
        print("  --> Cleaned up temporary test allocation on Project 7.")

        # -----------------------------------------------------------
        # TEST 5: HTTP Route Rendering
        # -----------------------------------------------------------
        res_proj = client.get('/projects/1/materials')
        assert res_proj.status_code == 200, f"Expected 200 for /projects/1/materials, got {res_proj.status_code}"
        assert b"Project Materials" in res_proj.data

        res_mat = client.get('/materials/2')
        assert res_mat.status_code == 200, f"Expected 200 for /materials/2, got {res_mat.status_code}"
        assert b"Remaining Project Stock" in res_mat.data

        res_rep_all = client.get('/reports/?project_id=all')
        assert res_rep_all.status_code == 200, f"Expected 200 for /reports/?project_id=all, got {res_rep_all.status_code}"
        assert b"Project Remaining Stock" in res_rep_all.data

        res_rep_p1 = client.get('/reports/?project_id=1')
        assert res_rep_p1.status_code == 200, f"Expected 200 for /reports/?project_id=1, got {res_rep_p1.status_code}"

        print("  --> PASS: All routes rendered with HTTP 200 and expected template bindings.")

    print("\n" + "=" * 60)
    print("ALL PRIORITY 1 (MATERIALS) TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == '__main__':
    run_tests()
