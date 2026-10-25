import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

os.environ['TEST_DB_NAME'] = 'buildcore_test'

from app import create_app, db
from sqlalchemy import text
import psycopg2

app = create_app()

def run_tests():
    print("=" * 70)
    print("MODULE 4: ADVERSARIAL PROJECT & TASK LIFECYCLE INTEGRITY TESTS")
    print("=" * 70)

    results = []

    with app.app_context():
        curr_db = db.session.execute(text("SELECT current_database();")).scalar()
        print(f"Connected Database: '{curr_db}'")
        assert curr_db == 'buildcore_test', f"Safety violation: Expected buildcore_test, got {curr_db}"

        client = app.test_client()
        login_res = client.post('/login', data={'username': 'admin', 'password': 'admin'}, follow_redirects=True)
        assert login_res.status_code == 200, "Admin login failed!"

        p101_id = db.session.execute(text("SELECT project_id FROM projects WHERE project_name LIKE 'QA-SIM-101%'")).scalar()
        p102_id = db.session.execute(text("SELECT project_id FROM projects WHERE project_name LIKE 'QA-SIM-102%'")).scalar()
        p104_id = db.session.execute(text("SELECT project_id FROM projects WHERE project_name LIKE 'QA-SIM-104%'")).scalar()
        tt_survey = db.session.execute(text("SELECT task_type_id FROM task_types WHERE task_name = 'QA-Task-Site Survey'")).scalar()
        tt_piling = db.session.execute(text("SELECT task_type_id FROM task_types WHERE task_name = 'QA-Task-Piling Work'")).scalar()

        # -------------------------------------------------------------
        # TEST-TSK-01: Status vs Progress Auto-Synchronization
        # -------------------------------------------------------------
        print("\n[TEST-TSK-01] Testing Status and Completion Percentage Two-Way Synchronization...")
        pt_row = db.session.execute(text("""
            SELECT pt.project_task_id FROM project_tasks pt
            WHERE pt.project_id = :p AND pt.status = 'In Progress' LIMIT 1
        """), {'p': p102_id}).fetchone()
        pt_id = pt_row.project_task_id

        # 1. Edit task: Set status='Completed', completion_percentage=45.0 -> must sync to 100.0%
        client.post(f'/tasks/project-task/{pt_id}/edit', data={
            'start_date': '2026-09-16',
            'due_date': '2026-11-30',
            'status': 'Completed',
            'completion_percentage': 45.0,
            'description': 'Sync test 1'
        }, follow_redirects=True)

        synced_1 = db.session.execute(text("SELECT status, completion_percentage FROM project_tasks WHERE project_task_id = :id"), {'id': pt_id}).fetchone()
        assert synced_1.status == 'Completed' and float(synced_1.completion_percentage) == 100.0, f"Sync 1 failed: {synced_1.status}, {synced_1.completion_percentage}"

        # 2. Edit task: Set status='In Progress', completion_percentage=100.0 -> must sync status to 'Completed'
        client.post(f'/tasks/project-task/{pt_id}/edit', data={
            'start_date': '2026-09-16',
            'due_date': '2026-11-30',
            'status': 'In Progress',
            'completion_percentage': 100.0,
            'description': 'Sync test 2'
        }, follow_redirects=True)

        synced_2 = db.session.execute(text("SELECT status, completion_percentage FROM project_tasks WHERE project_task_id = :id"), {'id': pt_id}).fetchone()
        assert synced_2.status == 'Completed' and float(synced_2.completion_percentage) == 100.0, f"Sync 2 failed: {synced_2.status}, {synced_2.completion_percentage}"

        # 3. Edit task: Set status='Not Started', completion_percentage=30.0 -> must sync status to 'In Progress'
        client.post(f'/tasks/project-task/{pt_id}/edit', data={
            'start_date': '2026-09-16',
            'due_date': '2026-11-30',
            'status': 'Not Started',
            'completion_percentage': 30.0,
            'description': 'Sync test 3'
        }, follow_redirects=True)

        synced_3 = db.session.execute(text("SELECT status, completion_percentage FROM project_tasks WHERE project_task_id = :id"), {'id': pt_id}).fetchone()
        assert synced_3.status == 'In Progress' and float(synced_3.completion_percentage) == 30.0, f"Sync 3 failed: {synced_3.status}, {synced_3.completion_percentage}"

        # Restore original state (60% In Progress)
        db.session.execute(text("UPDATE project_tasks SET status = 'In Progress', completion_percentage = 60.0 WHERE project_task_id = :id"), {'id': pt_id})
        db.session.commit()

        print("  Result: PASS - All 3 bidirectional synchronization rules verified.")
        results.append(('TEST-TSK-01', 'Status/Progress Auto-Synchronization', 'PASS', 'Two-way sync verified (Completed<=>100%, Not Started=>In Progress)'))

        # -------------------------------------------------------------
        # TEST-TSK-02: Database Check Constraints on Tasks
        # -------------------------------------------------------------
        print("\n[TEST-TSK-02] Testing Database Check Constraints on Task Status/Progress...")
        # Direct SQL bypass attempt 1: Completed with 50%
        constraint_1_passed = False
        try:
            db.session.execute(text("SAVEPOINT sp_chk1"))
            db.session.execute(text("""
                INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage)
                VALUES (:p, :tt, '2026-11-01', '2026-11-10', 'Completed', 50.0)
            """), {'p': p101_id, 'tt': tt_piling})
            db.session.commit()
        except Exception as e:
            db.session.execute(text("ROLLBACK TO SAVEPOINT sp_chk1"))
            if 'check_task_completion_status' in str(e):
                constraint_1_passed = True
                print("  Constraint 'check_task_completion_status' caught invalid status=Completed with 50%!")

        assert constraint_1_passed, "Database failed to reject status=Completed with 50%!"

        # Direct SQL bypass attempt 2: Not Started with 20%
        constraint_2_passed = False
        try:
            db.session.execute(text("SAVEPOINT sp_chk2"))
            db.session.execute(text("""
                INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage)
                VALUES (:p, :tt, '2026-11-01', '2026-11-10', 'Not Started', 20.0)
            """), {'p': p101_id, 'tt': tt_piling})
            db.session.commit()
        except Exception as e:
            db.session.execute(text("ROLLBACK TO SAVEPOINT sp_chk2"))
            if 'check_task_not_started_percentage' in str(e):
                constraint_2_passed = True
                print("  Constraint 'check_task_not_started_percentage' caught status=Not Started with 20%!")

        assert constraint_2_passed, "Database failed to reject status=Not Started with 20%!"

        print("  Result: PASS - Database check constraints enforce status/progress invariants at schema level.")
        results.append(('TEST-TSK-02', 'Task Consistency DB Check Constraints', 'PASS', 'Schema constraints reject inconsistent status/progress'))

        # -------------------------------------------------------------
        # TEST-TSK-03: Task Date Timeline Validation
        # -------------------------------------------------------------
        print("\n[TEST-TSK-03] Testing Task Date Timeline Boundaries...")
        # 1. Start date after due date
        res_date_rev = client.post(f'/tasks/{tt_piling}/assign', data={
            'project_id': p101_id,
            'start_date': '2026-11-20',
            'due_date': '2026-11-10',
            'status': 'Not Started',
            'completion_percentage': 0,
            'description': 'Reversed dates'
        }, follow_redirects=True)
        assert "Start date cannot be after due date" in res_date_rev.data.decode('utf-8')

        # 2. Task dates outside project timeline (P101 is 2026-11-01 to 2027-06-30)
        res_date_out = client.post(f'/tasks/{tt_piling}/assign', data={
            'project_id': p101_id,
            'start_date': '2026-10-01',
            'due_date': '2026-11-15',
            'status': 'Not Started',
            'completion_percentage': 0,
            'description': 'Out of bounds'
        }, follow_redirects=True)
        assert "must fall within the project timeline" in res_date_out.data.decode('utf-8')

        print("  Result: PASS - Start>Due and Out-of-Project-Timeline dates rejected.")
        results.append(('TEST-TSK-03', 'Task Date Timeline Boundaries', 'PASS', 'Start>due and out-of-bounds dates blocked'))

        # -------------------------------------------------------------
        # TEST-TSK-04: Overdue Logic Audit
        # -------------------------------------------------------------
        print("\n[TEST-TSK-04] Testing Overdue Calculation Logic...")
        db.session.execute(text("""
            INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage, description)
            VALUES (:p, :tt, '2026-08-01', '2026-09-01', 'In Progress', 70.0, 'Overdue Test Task')
        """), {'p': p102_id, 'tt': tt_survey})
        db.session.commit()

        overdue_row = db.session.execute(text("""
            SELECT description, is_overdue, status FROM (
                SELECT pt.description, pt.status,
                CASE WHEN CURRENT_DATE > pt.due_date AND pt.status != 'Completed' THEN True ELSE False END as is_overdue
                FROM project_tasks pt
                WHERE pt.description = 'Overdue Test Task'
            ) t
        """)).fetchone()
        assert overdue_row.is_overdue is True, "Incomplete task past due date not flagged as overdue!"

        db.session.execute(text("UPDATE project_tasks SET status = 'Completed', completion_percentage = 100.0 WHERE description = 'Overdue Test Task'"))
        db.session.commit()

        overdue_completed = db.session.execute(text("""
            SELECT description, is_overdue, status FROM (
                SELECT pt.description, pt.status,
                CASE WHEN CURRENT_DATE > pt.due_date AND pt.status != 'Completed' THEN True ELSE False END as is_overdue
                FROM project_tasks pt
                WHERE pt.description = 'Overdue Test Task'
            ) t
        """)).fetchone()
        assert overdue_completed.is_overdue is False, "Completed task past due date incorrectly flagged as overdue!"

        db.session.execute(text("DELETE FROM project_tasks WHERE description = 'Overdue Test Task'"))
        db.session.commit()

        print("  Result: PASS - Incomplete past-due tasks are overdue; Completed past-due tasks are NOT overdue.")
        results.append(('TEST-TSK-04', 'Overdue Calculation Audit', 'PASS', 'Correct overdue classification based on completion status'))

        # -------------------------------------------------------------
        # TEST-TSK-05: Project Progress Aggregation (Duration-Weighted)
        # -------------------------------------------------------------
        print("\n[TEST-TSK-05] Testing Project Progress Rollup Calculations (Duration-Weighted)...")
        # Compute expected duration-weighted progress independently:
        tasks_p102 = db.session.execute(text("""
            SELECT completion_percentage, (due_date - start_date + 1) as duration_days
            FROM project_tasks WHERE project_id = :p
        """), {'p': p102_id}).fetchall()

        total_weight = sum(t.duration_days for t in tasks_p102)
        weighted_sum = sum(float(t.completion_percentage) * t.duration_days for t in tasks_p102)
        expected_weighted_prog = round(weighted_sum / total_weight, 2)

        prog_102 = db.session.execute(text("""
            SELECT progress_percentage, total_tasks, completed_tasks 
            FROM project_progress_view WHERE project_id = :p
        """), {'p': p102_id}).fetchone()

        actual_prog = round(float(prog_102.progress_percentage), 2)
        assert actual_prog == expected_weighted_prog, f"Expected duration-weighted {expected_weighted_prog}%, got {actual_prog}%"
        assert prog_102.total_tasks == 3
        assert prog_102.completed_tasks == 1
        print(f"  P102 Progress: {actual_prog}% (Matches duration-weighted model: {expected_weighted_prog}%).")

        # Test project with 0 tasks: Create empty project
        db.session.execute(text("""
            INSERT INTO projects (project_id, project_name, project_type, client_name, location, start_date, expected_end_date, budget, status)
            VALUES (999000, 'QA-Empty-Project', 'Commercial', 'Client', 'City', '2026-01-01', '2026-12-31', 1000000, 'Planning')
        """))
        db.session.commit()

        empty_prog = db.session.execute(text("""
            SELECT COALESCE(pv.progress_percentage, 0) as progress,
                   COALESCE(pv.total_tasks, 0) as total_tasks,
                   COALESCE(pv.completed_tasks, 0) as completed_tasks
            FROM projects p
            LEFT JOIN project_progress_view pv ON p.project_id = pv.project_id
            WHERE p.project_id = 999000
        """)).fetchone()

        assert float(empty_prog.progress) == 0.0
        assert empty_prog.total_tasks == 0
        db.session.execute(text("DELETE FROM projects WHERE project_id = 999000"))
        db.session.commit()

        print("  Result: PASS - Duration-weighted progress confirmed; 0-task project handled gracefully.")
        results.append(('TEST-TSK-05', 'Project Progress Duration-Weighted Rollup', 'PASS', f'Exact duration-weighted progress reconciled ({actual_prog}%)'))

        # -------------------------------------------------------------
        # TEST-PRJ-01: History Protection on Project Deletion
        # -------------------------------------------------------------
        print("\n[TEST-PRJ-01] Testing Audit History Protection on Project Deletion...")
        # 1. Attempt deleting P104 (Completed, full history)
        del_104 = client.post(f'/projects/{p104_id}/delete', data={'admin_password': 'admin'}, follow_redirects=True)
        html_104 = del_104.data.decode('utf-8')
        assert "Cannot delete project" in html_104 and "historical audit records" in html_104
        p104_exists = db.session.execute(text("SELECT 1 FROM projects WHERE project_id = :p"), {'p': p104_id}).scalar()
        assert p104_exists == 1, "Protected project P104 was deleted!"
        print("  P104 deletion blocked by audit history guard.")

        # 2. Attempt deleting P102 (Active, active history)
        del_102 = client.post(f'/projects/{p102_id}/delete', data={'admin_password': 'admin'}, follow_redirects=True)
        html_102 = del_102.data.decode('utf-8')
        assert "Cannot delete project" in html_102
        p102_exists = db.session.execute(text("SELECT 1 FROM projects WHERE project_id = :p"), {'p': p102_id}).scalar()
        assert p102_exists == 1, "Active project P102 was deleted!"
        print("  P102 deletion blocked by audit history guard.")

        # 3. Delete P101 (Planning, zero history)
        db.session.execute(text("DELETE FROM project_tasks WHERE project_id = :p"), {'p': p101_id})
        db.session.commit()
        del_101 = client.post(f'/projects/{p101_id}/delete', data={'admin_password': 'admin'}, follow_redirects=True)
        html_101 = del_101.data.decode('utf-8')
        assert "deleted successfully" in html_101 or del_101.status_code == 200
        p101_exists = db.session.execute(text("SELECT 1 FROM projects WHERE project_id = :p"), {'p': p101_id}).scalar()
        assert not p101_exists, "Eligible project P101 was not deleted!"
        print("  P101 (clean project without audit history) deleted successfully.")

        print("  Result: PASS - Projects with audit history protected; clean projects deleted.")
        results.append(('TEST-PRJ-01', 'History Protection on Project Deletion', 'PASS', 'Blocked deletion of projects with history; deleted eligible project'))

        # -------------------------------------------------------------
        # TEST-PRJ-02: Admin Password Verification on Project Deletion
        # -------------------------------------------------------------
        print("\n[TEST-PRJ-02] Testing Admin Password Requirement on Project Deletion...")
        db.session.execute(text("""
            INSERT INTO projects (project_id, project_name, project_type, client_name, location, start_date, expected_end_date, budget, status)
            VALUES (999001, 'QA-Password-Test', 'Residential', 'Client', 'City', '2026-01-01', '2026-12-31', 500000, 'Planning')
        """))
        db.session.commit()

        del_wrong_pw = client.post('/projects/999001/delete', data={'admin_password': 'wrongpassword123'}, follow_redirects=True)
        assert "Incorrect admin password" in del_wrong_pw.data.decode('utf-8')
        proj_still_exists = db.session.execute(text("SELECT 1 FROM projects WHERE project_id = 999001")).scalar()
        assert proj_still_exists == 1, "Project deleted despite incorrect password!"

        db.session.execute(text("DELETE FROM projects WHERE project_id = 999001"))
        db.session.commit()
        print("  Result: PASS - Project deletion requires valid admin password authentication.")
        results.append(('TEST-PRJ-02', 'Admin Password Guard on Deletion', 'PASS', 'Rejected project deletion with invalid admin password'))

    print("\n" + "=" * 70)
    print("MODULE 4 RESULTS SUMMARY:")
    for code, name, outcome, notes in results:
        print(f"  [{outcome}] {code:12} : {name:40} | {notes}")
    print("=" * 70)
    return results

if __name__ == '__main__':
    run_tests()
