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
    print("RUNNING VERIFICATION TESTS: PRIORITY 5 — HISTORY PROTECTION")
    print("=" * 60)

    with app.app_context():
        # Verify active database
        active_db = db.session.execute(text("SELECT current_database();")).scalar()
        print(f"Active test database: '{active_db}'")
        assert active_db in ('buildcore_copy', 'buildcore_test'), "Safety failure: Not running on buildcore_copy!"

        client = app.test_client()
        with client.session_transaction() as sess:
            sess['_user_id'] = '1'

        # -----------------------------------------------------------
        # TEST 1: Deletion Blocked for Project with Historical Records
        # -----------------------------------------------------------
        print("\n[TEST 1] Testing Deletion Guard on Active/Historical Project 1...")
        # Project 1 has purchases, tasks, worker assignments, expenses
        res_del_p1 = client.post('/projects/1/delete', data={
            'admin_password': 'admin'
        }, follow_redirects=True)

        assert b"Cannot delete project" in res_del_p1.data
        assert b"historical audit records" in res_del_p1.data
        print("  --> PASS: Deletion safely blocked by History Guard.")

        # Verify Project 1 and its child records still exist
        p1 = db.session.execute(text("SELECT project_id, project_name FROM projects WHERE project_id = 1")).fetchone()
        assert p1 is not None, "Project 1 was deleted despite safety guard!"
        po_count = db.session.execute(text("SELECT COUNT(*) FROM purchases WHERE project_id = 1")).scalar()
        assert po_count > 0, "Purchases for Project 1 were wiped out!"
        print(f"  --> PASS: Project 1 ('{p1.project_name}') intact with all {po_count} purchase orders and audit trails.")

        # -----------------------------------------------------------
        # TEST 2: Password Authentication Verification
        # -----------------------------------------------------------
        print("\n[TEST 2] Testing Password Authentication Guard...")
        res_bad_pw = client.post('/projects/1/delete', data={
            'admin_password': 'wrongpassword123'
        }, follow_redirects=True)
        assert b"Incorrect admin password" in res_bad_pw.data
        print("  --> PASS: Rejected deletion attempt with invalid password.")

        # -----------------------------------------------------------
        # TEST 3: Deletion of Pure Draft Project (No Transactions)
        # -----------------------------------------------------------
        print("\n[TEST 3] Testing Deletion of Unused Draft Project...")
        # Create a clean draft project with zero transactions
        draft_p_id = db.session.execute(text("""
            INSERT INTO projects (project_name, project_type, client_name, location, start_date, expected_end_date, budget, status)
            VALUES ('__Draft_Empty_Project__', 'Residential', 'Draft Client', 'Draft City', '2026-11-01', '2027-04-30', 500000.00, 'Planned')
            RETURNING project_id
        """)).scalar()
        db.session.commit()

        # Delete draft project with correct admin password
        res_del_draft = client.post(f'/projects/{draft_p_id}/delete', data={
            'admin_password': 'admin'
        }, follow_redirects=True)

        assert b"deleted successfully" in res_del_draft.data
        draft_check = db.session.execute(text(f"SELECT COUNT(*) FROM projects WHERE project_id = {draft_p_id}")).scalar()
        assert draft_check == 0, "Draft project was not deleted!"
        print("  --> PASS: Draft project with zero audit history deleted successfully.")

        # -----------------------------------------------------------
        # TEST 4: Legacy project_workers Table Audit
        # -----------------------------------------------------------
        print("\n[TEST 4] Verifying Legacy project_workers Deprecation & Catalog Documentation...")
        # Check database comment on project_workers
        pw_comment = db.session.execute(text("""
            SELECT obj_description(oid) 
            FROM pg_class 
            WHERE relname = 'project_workers'
        """)).scalar()
        
        print(f"  PostgreSQL Catalog Description: '{pw_comment}'")
        assert pw_comment is not None and "DEPRECATED" in pw_comment
        print("  --> PASS: Legacy project_workers table properly cataloged as DEPRECATED without breaking schema.")

        # -----------------------------------------------------------
        # TEST 5: HTTP 200 Route Rendering
        # -----------------------------------------------------------
        print("\n[TEST 5] Testing Project Management Route Rendering...")
        assert client.get('/projects/').status_code == 200
        assert client.get('/projects/1').status_code == 200
        assert client.get('/projects/1/edit').status_code == 200
        print("  --> PASS: All project routes rendered HTTP 200.")

    print("\n" + "=" * 60)
    print("ALL PRIORITY 5 (HISTORY PROTECTION) TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == '__main__':
    run_tests()
