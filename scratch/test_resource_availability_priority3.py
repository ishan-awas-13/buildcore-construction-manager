import os
import sys
import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

from app import create_app, db
from sqlalchemy import text

app = create_app()

def run_tests():
    print("=" * 60)
    print("RUNNING VERIFICATION TESTS: PRIORITY 3 — RESOURCE AVAILABILITY")
    print("=" * 60)

    with app.app_context():
        # Verify active database
        active_db = db.session.execute(text("SELECT current_database();")).scalar()
        print(f"Active test database: '{active_db}'")
        assert active_db in ('buildcore_copy', 'buildcore_test'), "Safety failure: Not running on buildcore_copy!"

        client = app.test_client()
        with client.session_transaction() as sess:
            sess['_user_id'] = '1'

        # Create a temporary project for availability testing to avoid task_type uniqueness collisions
        temp_project_id = db.session.execute(text("""
            INSERT INTO projects (project_name, project_type, client_name, location, start_date, expected_end_date, budget, status)
            VALUES ('__Test_Resource_Project__', 'Commercial', 'Test Client', 'Test City', '2026-01-01', '2028-12-31', 5000000.00, 'Active')
            RETURNING project_id
        """)).scalar()
        db.session.commit()

        try:
            # -----------------------------------------------------------
            # TEST 1: worker_status_view Date-Range & Future Task Logic
            # -----------------------------------------------------------
            print("\n[TEST 1] Testing worker_status_view with Future Tasks...")
            # Create a future task: starts in 2028
            future_task_id = db.session.execute(text("""
                INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage)
                VALUES (:p_id, 1, '2028-01-01', '2028-06-30', 'Not Started', 0)
                RETURNING project_task_id
            """), {'p_id': temp_project_id}).scalar()
            
            # Pick worker 15 (currently Available)
            worker_id_test = 15
            db.session.execute(text("""
                INSERT INTO task_workers (project_task_id, worker_id, assigned_hours, locked_daily_rate)
                VALUES (:pt_id, :w_id, 80, 1000.00)
            """), {'pt_id': future_task_id, 'w_id': worker_id_test})
            db.session.commit()

            # Check computed_status in worker_status_view
            status_today = db.session.execute(text("""
                SELECT computed_status FROM worker_status_view WHERE worker_id = :w_id
            """), {'w_id': worker_id_test}).scalar()

            print(f"  Worker {worker_id_test} assigned to Future Task ({future_task_id}) in 2028. Computed Status Today: '{status_today}'")
            assert status_today == 'Available', f"Expected 'Available' for future task assignment, got '{status_today}'"
            print("  --> PASS: Future task assignments do not falsely mark workers as unavailable today.")

            # Clean up Test 1 task & assignment
            db.session.execute(text(f"DELETE FROM task_workers WHERE project_task_id = {future_task_id}"))
            db.session.execute(text(f"DELETE FROM project_tasks WHERE project_task_id = {future_task_id}"))
            db.session.commit()

            # -----------------------------------------------------------
            # TEST 2: Reject Inactive / On-Leave Workers
            # -----------------------------------------------------------
            print("\n[TEST 2] Testing Rejection of Inactive or On-Leave Workers...")
            # Create a task in temp project
            test_task_id = db.session.execute(text("""
                INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage)
                VALUES (:p_id, 1, '2026-11-01', '2026-12-31', 'In Progress', 10)
                RETURNING project_task_id
            """), {'p_id': temp_project_id}).scalar()

            leave_worker_id = db.session.execute(text("""
                INSERT INTO workers (name, role, skill, phone, daily_rate, status)
                VALUES ('Test Leave Worker', 'Laborer', 'General', '9999900001', 800.00, 'On Leave')
                RETURNING worker_id
            """)).scalar()
            db.session.commit()

            res_assign_leave = client.post(f'/workers/{leave_worker_id}/assign', data={
                'project_task_id': str(test_task_id),
                'assigned_hours': '40'
            }, follow_redirects=True)

            assert b"Worker status is currently &#39;On Leave&#39;" in res_assign_leave.data or b"Worker status is currently 'On Leave'" in res_assign_leave.data
            tw_count = db.session.execute(text(f"SELECT COUNT(*) FROM task_workers WHERE worker_id = {leave_worker_id}")).scalar()
            assert tw_count == 0, "On Leave worker was assigned despite restriction!"
            print("  --> PASS: Rejected assignment for worker marked 'On Leave'.")

            # Clean up Test 2 worker and task
            db.session.execute(text(f"DELETE FROM workers WHERE worker_id = {leave_worker_id}"))
            db.session.execute(text(f"DELETE FROM project_tasks WHERE project_task_id = {test_task_id}"))
            db.session.commit()

            # -----------------------------------------------------------
            # TEST 3: Schedule Conflict Validation
            # -----------------------------------------------------------
            print("\n[TEST 3] Testing Schedule Conflict Prevention on Workers...")
            # Create Task A (2027-01-01 to 2027-02-28) and Task B overlapping (2027-02-01 to 2027-03-31)
            task_a = db.session.execute(text("""
                INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage)
                VALUES (:p_id, 1, '2027-01-01', '2027-02-28', 'In Progress', 10)
                RETURNING project_task_id
            """), {'p_id': temp_project_id}).scalar()
            task_b = db.session.execute(text("""
                INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage)
                VALUES (:p_id, 2, '2027-02-01', '2027-03-31', 'In Progress', 0)
                RETURNING project_task_id
            """), {'p_id': temp_project_id}).scalar()
            task_c_no_overlap = db.session.execute(text("""
                INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage)
                VALUES (:p_id, 3, '2027-05-01', '2027-06-30', 'Not Started', 0)
                RETURNING project_task_id
            """), {'p_id': temp_project_id}).scalar()
            db.session.commit()

            # Assign worker 16 to Task A
            res_a = client.post('/workers/16/assign', data={
                'project_task_id': str(task_a),
                'assigned_hours': '50'
            }, follow_redirects=True)
            assert b"Worker assigned to task successfully" in res_a.data
            print("  --> Assigned worker 16 to initial Task A.")

            # Attempt to assign worker 16 to overlapping Task B
            res_b = client.post('/workers/16/assign', data={
                'project_task_id': str(task_b),
                'assigned_hours': '40'
            }, follow_redirects=True)
            assert b"Schedule conflict" in res_b.data
            print("  --> PASS: Blocked overlapping schedule assignment for Task B.")

            # Attempt to assign worker 16 to non-overlapping Task C
            res_c = client.post('/workers/16/assign', data={
                'project_task_id': str(task_c_no_overlap),
                'assigned_hours': '40'
            }, follow_redirects=True)
            assert b"Worker assigned to task successfully" in res_c.data
            print("  --> PASS: Allowed valid non-overlapping schedule assignment for Task C.")

            # Clean up Test 3 tasks
            db.session.execute(text(f"DELETE FROM task_workers WHERE project_task_id IN ({task_a}, {task_b}, {task_c_no_overlap})"))
            db.session.execute(text(f"DELETE FROM project_tasks WHERE project_task_id IN ({task_a}, {task_b}, {task_c_no_overlap})"))
            db.session.commit()

            # -----------------------------------------------------------
            # TEST 4: Equipment Maintenance / Retired Rejection
            # -----------------------------------------------------------
            print("\n[TEST 4] Testing Rejection of Maintenance/Retired Equipment...")
            eq_maint = db.session.execute(text("SELECT equipment_id, equipment_name, status FROM equipment WHERE status = 'Maintenance' LIMIT 1")).fetchone()
            assert eq_maint is not None, "Need a Maintenance equipment record for test"

            # Create a task in temp project for equipment assignment
            eq_task_id = db.session.execute(text("""
                INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage)
                VALUES (:p_id, 1, '2027-01-01', '2027-01-31', 'In Progress', 0)
                RETURNING project_task_id
            """), {'p_id': temp_project_id}).scalar()
            db.session.commit()

            res_eq_assign = client.post(f'/equipment/{eq_maint.equipment_id}/assign', data={
                'project_task_id': str(eq_task_id),
                'start_date': '2027-01-01',
                'end_date': '2027-01-10',
                'hours_used': '20'
            }, follow_redirects=True)
            assert b"Equipment is currently in &#39;Maintenance&#39; status" in res_eq_assign.data or b"Equipment is currently in 'Maintenance' status" in res_eq_assign.data
            
            ea_count = db.session.execute(text(f"SELECT COUNT(*) FROM equipment_assignments WHERE equipment_id = {eq_maint.equipment_id} AND start_date = '2027-01-01'")).scalar()
            assert ea_count == 0, "Maintenance equipment was assigned despite restriction!"
            print(f"  --> PASS: Rejected assignment for equipment '{eq_maint.equipment_name}' under Maintenance.")

            # Clean up Test 4 task
            db.session.execute(text(f"DELETE FROM project_tasks WHERE project_task_id = {eq_task_id}"))
            db.session.commit()

            # -----------------------------------------------------------
            # TEST 5: Dashboard Equipment Count from View
            # -----------------------------------------------------------
            print("\n[TEST 5] Testing Dashboard Available Equipment Count...")
            computed_avail = db.session.execute(text("SELECT COUNT(*) FROM equipment_status_view WHERE computed_status = 'Available'")).scalar()
            res_dash = client.get('/dashboard/')
            assert res_dash.status_code == 200
            assert f"{computed_avail} Equip Available".encode('utf-8') in res_dash.data
            print(f"  --> PASS: Dashboard displays {computed_avail} available equipment reflecting computed status.")

            # -----------------------------------------------------------
            # TEST 6: HTTP 200 Route Rendering
            # -----------------------------------------------------------
            print("\n[TEST 6] Testing HTTP Route Rendering...")
            assert client.get('/workers/').status_code == 200
            assert client.get('/workers/1').status_code == 200
            assert client.get('/equipment/').status_code == 200
            assert client.get('/equipment/1').status_code == 200
            print("  --> PASS: All resource management routes rendered HTTP 200.")

        finally:
            # Clean up temporary test project
            db.session.execute(text(f"DELETE FROM project_tasks WHERE project_id = {temp_project_id}"))
            db.session.execute(text(f"DELETE FROM projects WHERE project_id = {temp_project_id}"))
            db.session.commit()
            print("  --> Cleaned up temporary test project.")

    print("\n" + "=" * 60)
    print("ALL PRIORITY 3 (RESOURCE AVAILABILITY) TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == '__main__':
    run_tests()
