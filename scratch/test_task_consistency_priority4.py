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
    print("RUNNING VERIFICATION TESTS: PRIORITY 4 — TASK CONSISTENCY")
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
        # TEST 1: Database Check Constraints
        # -----------------------------------------------------------
        print("\n[TEST 1] Testing Database Check Constraints on project_tasks...")
        
        # 1a: Completed with < 100% must be rejected by check_task_completion_status
        completed_task_id = db.session.execute(text("SELECT project_task_id FROM project_tasks WHERE status = 'Completed' LIMIT 1")).scalar()
        try:
            db.session.execute(text("SAVEPOINT sp_test1a"))
            db.session.execute(text("""
                UPDATE project_tasks SET completion_percentage = 75.00 WHERE project_task_id = :id
            """), {'id': completed_task_id})
            db.session.commit()
            assert False, "Failed to reject status='Completed' with completion_percentage < 100!"
        except Exception as e:
            db.session.execute(text("ROLLBACK TO SAVEPOINT sp_test1a"))
            print("  --> PASS: DB rejected 'Completed' status with 75% progress via constraint.")

        # 1b: In Progress with 100% must be rejected by check_task_completion_status
        in_progress_task_id = db.session.execute(text("SELECT project_task_id FROM project_tasks WHERE status = 'In Progress' LIMIT 1")).scalar()
        try:
            db.session.execute(text("SAVEPOINT sp_test1b"))
            db.session.execute(text("""
                UPDATE project_tasks SET completion_percentage = 100.00 WHERE project_task_id = :id
            """), {'id': in_progress_task_id})
            db.session.commit()
            assert False, "Failed to reject status='In Progress' with completion_percentage = 100!"
        except Exception as e:
            db.session.execute(text("ROLLBACK TO SAVEPOINT sp_test1b"))
            print("  --> PASS: DB rejected 'In Progress' status with 100% progress via constraint.")

        # 1c: Not Started with > 0% must be rejected by check_task_not_started_percentage
        not_started_task_id = db.session.execute(text("SELECT project_task_id FROM project_tasks WHERE status = 'Not Started' LIMIT 1")).scalar()
        try:
            db.session.execute(text("SAVEPOINT sp_test1c"))
            db.session.execute(text("""
                UPDATE project_tasks SET completion_percentage = 25.00 WHERE project_task_id = :id
            """), {'id': not_started_task_id})
            db.session.commit()
            assert False, "Failed to reject status='Not Started' with completion_percentage > 0!"
        except Exception as e:
            db.session.execute(text("ROLLBACK TO SAVEPOINT sp_test1c"))
            print("  --> PASS: DB rejected 'Not Started' status with 25% progress via constraint.")

        # -----------------------------------------------------------
        # TEST 2: Reconciled Data Integrity Audit
        # -----------------------------------------------------------
        print("\n[TEST 2] Auditing Database Table project_tasks for Zero Inconsistencies...")
        inconsistent_rows = db.session.execute(text("""
            SELECT project_task_id, project_id, status, completion_percentage
            FROM project_tasks
            WHERE (status = 'Completed' AND completion_percentage != 100)
               OR (status != 'Completed' AND completion_percentage = 100)
               OR (status = 'Not Started' AND completion_percentage != 0)
        """)).fetchall()

        assert len(inconsistent_rows) == 0, f"Found inconsistent rows in project_tasks: {inconsistent_rows}"
        print(f"  Total inconsistent task rows in database: {len(inconsistent_rows)}")

        # Verify Tasks 24, 25, 26 specifically
        reconciled_tasks = db.session.execute(text("""
            SELECT project_task_id, project_id, status, completion_percentage
            FROM project_tasks
            WHERE project_task_id IN (24, 25, 26)
            ORDER BY project_task_id
        """)).fetchall()
        for r in reconciled_tasks:
            print(f"  Task {r.project_task_id} (Project {r.project_id}): status='{r.status}', progress={r.completion_percentage}%")
            assert r.status == 'Completed' and float(r.completion_percentage) == 100.0
        print("  --> PASS: All existing tasks (including 24, 25, 26) are 100% consistent.")

        # -----------------------------------------------------------
        # TEST 3: Route Synchronization Workflows (Flask Test Client)
        # -----------------------------------------------------------
        print("\n[TEST 3] Testing Route Status & Progress Auto-Synchronization...")
        # Create a temporary project and task
        temp_p_id = db.session.execute(text("""
            INSERT INTO projects (project_name, project_type, client_name, location, start_date, expected_end_date, budget, status)
            VALUES ('__Task_Sync_Test_Project__', 'Industrial', 'Sync Client', 'City', '2026-01-01', '2027-12-31', 1000000, 'Active')
            RETURNING project_id
        """)).scalar()
        
        test_pt_id = db.session.execute(text("""
            INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage)
            VALUES (:p_id, 1, '2026-02-01', '2026-08-31', 'In Progress', 20.00)
            RETURNING project_task_id
        """), {'p_id': temp_p_id}).scalar()
        db.session.commit()

        try:
            # 3a: User sets status='Completed' but leaves progress=45% -> should auto-sync to 100%
            res_3a = client.post(f'/tasks/project-task/{test_pt_id}/edit', data={
                'start_date': '2026-02-01',
                'due_date': '2026-08-31',
                'status': 'Completed',
                'completion_percentage': '45',
                'description': 'Sync test 3a'
            }, follow_redirects=True)
            assert res_3a.status_code == 200
            row_3a = db.session.execute(text(f"SELECT status, completion_percentage FROM project_tasks WHERE project_task_id = {test_pt_id}")).fetchone()
            assert row_3a.status == 'Completed' and float(row_3a.completion_percentage) == 100.0
            print("  --> PASS: Status 'Completed' with 45% input auto-synchronized to 100% in DB.")

            # 3b: User sets progress=100% but leaves status='In Progress' -> should auto-sync to 'Completed'
            res_3b = client.post(f'/tasks/project-task/{test_pt_id}/edit', data={
                'start_date': '2026-02-01',
                'due_date': '2026-08-31',
                'status': 'In Progress',
                'completion_percentage': '100',
                'description': 'Sync test 3b'
            }, follow_redirects=True)
            assert res_3b.status_code == 200
            row_3b = db.session.execute(text(f"SELECT status, completion_percentage FROM project_tasks WHERE project_task_id = {test_pt_id}")).fetchone()
            assert row_3b.status == 'Completed' and float(row_3b.completion_percentage) == 100.0
            print("  --> PASS: Progress 100% with 'In Progress' status auto-synchronized to 'Completed' in DB.")

            # 3c: User sets status='Not Started' with progress=50% -> should auto-transition to 'In Progress'
            res_3c = client.post(f'/tasks/project-task/{test_pt_id}/edit', data={
                'start_date': '2026-02-01',
                'due_date': '2026-08-31',
                'status': 'Not Started',
                'completion_percentage': '50',
                'description': 'Sync test 3c'
            }, follow_redirects=True)
            assert res_3c.status_code == 200
            row_3c = db.session.execute(text(f"SELECT status, completion_percentage FROM project_tasks WHERE project_task_id = {test_pt_id}")).fetchone()
            assert row_3c.status == 'In Progress' and float(row_3c.completion_percentage) == 50.0
            print("  --> PASS: Status 'Not Started' with 50% input auto-transitioned to 'In Progress' in DB.")

            # 3d: Out of bounds percentage rejected
            res_3d = client.post(f'/tasks/project-task/{test_pt_id}/edit', data={
                'start_date': '2026-02-01',
                'due_date': '2026-08-31',
                'status': 'In Progress',
                'completion_percentage': '150',
                'description': 'Sync test 3d'
            }, follow_redirects=True)
            assert b"Completion percentage must be between 0 and 100" in res_3d.data
            print("  --> PASS: Out of bounds (150%) completion percentage rejected.")

        finally:
            db.session.execute(text(f"DELETE FROM project_tasks WHERE project_id = {temp_p_id}"))
            db.session.execute(text(f"DELETE FROM projects WHERE project_id = {temp_p_id}"))
            db.session.commit()
            print("  --> Cleaned up temporary test project.")

        # -----------------------------------------------------------
        # TEST 4: Project Progress View Consistency
        # -----------------------------------------------------------
        print("\n[TEST 4] Testing project_progress_view Consistency on Project 7...")
        p7_progress = db.session.execute(text("""
            SELECT total_tasks, completed_tasks, progress_percentage 
            FROM project_progress_view 
            WHERE project_id = 7
        """)).fetchone()
        
        print(f"  Project 7: total_tasks={p7_progress.total_tasks}, completed_tasks={p7_progress.completed_tasks}, progress={p7_progress.progress_percentage}%")
        assert p7_progress.total_tasks == 4
        assert p7_progress.completed_tasks == 4
        assert float(p7_progress.progress_percentage) == 100.0
        print("  --> PASS: Project 7 progress view reports 4/4 completed tasks and 100% progress.")

        # -----------------------------------------------------------
        # TEST 5: HTTP 200 Route Rendering
        # -----------------------------------------------------------
        print("\n[TEST 5] Testing HTTP Route Rendering...")
        assert client.get('/tasks/').status_code == 200
        assert client.get('/tasks/1').status_code == 200
        assert client.get('/tasks/1/assign').status_code == 200
        assert client.get('/tasks/project-task/1/edit').status_code == 200
        print("  --> PASS: All task routes rendered HTTP 200.")

    print("\n" + "=" * 60)
    print("ALL PRIORITY 4 (TASK CONSISTENCY) TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == '__main__':
    run_tests()
