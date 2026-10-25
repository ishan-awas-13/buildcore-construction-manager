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
    print("MODULE 2: ADVERSARIAL RESOURCE SCHEDULING & AVAILABILITY TESTS")
    print("=" * 70)

    results = []

    with app.app_context():
        curr_db = db.session.execute(text("SELECT current_database();")).scalar()
        print(f"Connected Database: '{curr_db}'")
        assert curr_db == 'buildcore_test', f"Safety violation: Expected buildcore_test, got {curr_db}"

        client = app.test_client()
        login_res = client.post('/login', data={'username': 'admin', 'password': 'admin'}, follow_redirects=True)
        assert login_res.status_code == 200, "Admin login failed!"

        # Query IDs
        p102_id = db.session.execute(text("SELECT project_id FROM projects WHERE project_name LIKE 'QA-SIM-102%'")).scalar()
        p103_id = db.session.execute(text("SELECT project_id FROM projects WHERE project_name LIKE 'QA-SIM-103%'")).scalar()

        w_anil_id = db.session.execute(text("SELECT worker_id FROM workers WHERE name LIKE 'QA-Worker-Anil%'")).scalar()
        w_bikram_id = db.session.execute(text("SELECT worker_id FROM workers WHERE name LIKE 'QA-Worker-Bikram%'")).scalar()
        w_deepak_id = db.session.execute(text("SELECT worker_id FROM workers WHERE name LIKE 'QA-Worker-Deepak%'")).scalar()
        w_eshwar_id = db.session.execute(text("SELECT worker_id FROM workers WHERE name LIKE 'QA-Worker-Eshwar%'")).scalar()

        eq_crane_id = db.session.execute(text("SELECT equipment_id FROM equipment WHERE equipment_name LIKE 'QA-Equip-Tower Crane%'")).scalar()
        eq_jcb_id = db.session.execute(text("SELECT equipment_id FROM equipment WHERE equipment_name LIKE 'QA-Equip-JCB Excavator%'")).scalar()
        eq_mixer_id = db.session.execute(text("SELECT equipment_id FROM equipment WHERE equipment_name LIKE 'QA-Equip-Transit Mixer%'")).scalar()

        # Task on P102 Task 2: 2026-09-16 to 2026-11-30 (In Progress)
        pt_102_2 = db.session.execute(text("""
            SELECT pt.project_task_id FROM project_tasks pt 
            JOIN task_types tt ON pt.task_type_id = tt.task_type_id
            WHERE pt.project_id = :p AND tt.task_name = 'QA-Task-Superstructure'
        """), {'p': p102_id}).scalar()

        # Task on P102 Task 3: 2026-12-01 to 2027-04-30 (Not Started)
        pt_102_3 = db.session.execute(text("""
            SELECT pt.project_task_id FROM project_tasks pt 
            JOIN task_types tt ON pt.task_type_id = tt.task_type_id
            WHERE pt.project_id = :p AND tt.task_name = 'QA-Task-Finishing'
        """), {'p': p102_id}).scalar()

        # Task on P103 Task 2: 2026-09-01 to 2026-12-20 (In Progress) -> Overlaps with pt_102_2!
        pt_103_2 = db.session.execute(text("""
            SELECT pt.project_task_id FROM project_tasks pt 
            JOIN task_types tt ON pt.task_type_id = tt.task_type_id
            WHERE pt.project_id = :p AND tt.task_name = 'QA-Task-Finishing'
        """), {'p': p103_id}).scalar()

        # -------------------------------------------------------------
        # TEST-RES-01: Concurrent Worker Conflict (Overlapping Active Tasks)
        # -------------------------------------------------------------
        print("\n[TEST-RES-01] Testing Concurrent Worker Conflict Detection...")
        res_overlap = client.post(f'/workers/{w_bikram_id}/assign', data={
            'project_task_id': pt_103_2,
            'assigned_hours': 40
        }, follow_redirects=True)
        html = res_overlap.data.decode('utf-8')
        assert "Schedule conflict" in html, f"Worker overlap not detected! HTML: {html[:300]}"
        assigned = db.session.execute(text("SELECT 1 FROM task_workers WHERE worker_id = :w AND project_task_id = :t"), {'w': w_bikram_id, 't': pt_103_2}).fetchone()
        assert not assigned, "Conflicting assignment written to database!"
        print("  Result: PASS - Schedule collision detected and blocked across projects.")
        results.append(('TEST-RES-01', 'Concurrent Worker Schedule Conflict Guard', 'PASS', 'Overlapping task assignment blocked across projects'))

        # -------------------------------------------------------------
        # TEST-RES-02: Non-Overlapping Cross-Project Worker Sharing
        # -------------------------------------------------------------
        print("\n[TEST-RES-02] Testing Non-Overlapping Cross-Project Worker Assignment...")
        # Check if already assigned
        already_assigned = db.session.execute(text("SELECT 1 FROM task_workers WHERE worker_id = :w AND project_task_id = :t"), {'w': w_bikram_id, 't': pt_102_3}).fetchone()
        if not already_assigned:
            res_valid_share = client.post(f'/workers/{w_bikram_id}/assign', data={
                'project_task_id': pt_102_3,
                'assigned_hours': 80
            }, follow_redirects=True)
            html = res_valid_share.data.decode('utf-8')
            assert "Worker assigned to task successfully" in html
        
        assigned_share = db.session.execute(text("SELECT assigned_hours FROM task_workers WHERE worker_id = :w AND project_task_id = :t"), {'w': w_bikram_id, 't': pt_102_3}).fetchone()
        assert assigned_share and float(assigned_share.assigned_hours) == 80.0
        print(f"  Result: PASS - Non-overlapping task assignment succeeded (Hours: {assigned_share.assigned_hours}).")
        results.append(('TEST-RES-02', 'Non-Overlapping Worker Sharing Across Tasks', 'PASS', 'Successfully assigned to subsequent non-overlapping task'))

        # -------------------------------------------------------------
        # TEST-RES-03: Inactive & On-Leave Worker Guards
        # -------------------------------------------------------------
        print("\n[TEST-RES-03] Testing Inactive & On-Leave Worker Guards...")
        # Deepak is 'On Leave'
        res_leave = client.post(f'/workers/{w_deepak_id}/assign', data={
            'project_task_id': pt_102_3,
            'assigned_hours': 40
        }, follow_redirects=True)
        assert "Cannot assign" in res_leave.data.decode('utf-8') and "On Leave" in res_leave.data.decode('utf-8')
        
        # Eshwar is 'Inactive'
        res_inact = client.post(f'/workers/{w_eshwar_id}/assign', data={
            'project_task_id': pt_102_3,
            'assigned_hours': 40
        }, follow_redirects=True)
        assert "Cannot assign" in res_inact.data.decode('utf-8') and "Inactive" in res_inact.data.decode('utf-8')
        
        print("  Result: PASS - 'On Leave' and 'Inactive' workers blocked from assignment.")
        results.append(('TEST-RES-03', 'Inactive/On-Leave Worker Assignment Guard', 'PASS', 'Blocked assignment of workers with non-active status'))

        # -------------------------------------------------------------
        # TEST-RES-04: Worker Master Rate Mutation vs Historical Rate Snapshot
        # -------------------------------------------------------------
        print("\n[TEST-RES-04] Testing Worker Historical Snapshot Immutability...")
        anil_rec = db.session.execute(text("""
            SELECT tw.locked_daily_rate, tw.assigned_hours, w.daily_rate 
            FROM task_workers tw
            JOIN workers w ON tw.worker_id = w.worker_id
            WHERE w.worker_id = :id LIMIT 1
        """), {'id': w_anil_id}).fetchone()
        original_locked = float(anil_rec.locked_daily_rate)
        print(f"  Anil's original master daily rate: ₹{anil_rec.daily_rate}, locked snapshot: ₹{original_locked}")

        # Update Anil's master daily rate in catalog to ₹3,500
        client.post(f'/workers/{w_anil_id}/edit', data={
            'name': 'QA-Worker-Anil (Site Eng)',
            'role': 'Engineer',
            'skill': 'Civil Engineering',
            'phone': '9123456780',
            'daily_rate': 3500.00,
            'status': 'Active'
        }, follow_redirects=True)

        # Check locked snapshot in task_workers
        after_locked = db.session.execute(text("""
            SELECT locked_daily_rate FROM task_workers WHERE worker_id = :id LIMIT 1
        """), {'id': w_anil_id}).scalar()
        assert float(after_locked) == original_locked, f"MUTATION LEAK: locked rate changed from {original_locked} to {after_locked}!"

        # Check expense_ledger_view labour cost for QA-Worker-Anil specifically
        ledger_cost = db.session.execute(text("""
            SELECT amount FROM expense_ledger_view WHERE category = 'Labour' AND description LIKE '%QA-Worker-Anil%' LIMIT 1
        """)).scalar()
        expected_cost = round((float(anil_rec.assigned_hours) / 8.0) * original_locked, 2)
        assert float(ledger_cost) == float(expected_cost), f"Ledger cost recalculated with master rate! Expected {expected_cost}, got {ledger_cost}"
        print(f"  Result: PASS - Historical cost preserved at ₹{ledger_cost} despite master rate increase to ₹3,500.")
        results.append(('TEST-RES-04', 'Worker Rate Snapshot Immutability', 'PASS', 'Historical locked rate and ledger immune to catalog rate change'))

        # -------------------------------------------------------------
        # TEST-RES-05: Equipment Maintenance & Retired Guards
        # -------------------------------------------------------------
        print("\n[TEST-RES-05] Testing Equipment Maintenance & Retired Guards...")
        # JCB is in 'Maintenance'
        res_jcb = client.post(f'/equipment/{eq_jcb_id}/assign', data={
            'project_task_id': pt_102_3,
            'start_date': '2026-12-05',
            'end_date': '2026-12-20',
            'hours_used': 20
        }, follow_redirects=True)
        assert "Cannot assign" in res_jcb.data.decode('utf-8') and "Maintenance" in res_jcb.data.decode('utf-8')

        # Transit Mixer is 'Retired'
        res_mixer = client.post(f'/equipment/{eq_mixer_id}/assign', data={
            'project_task_id': pt_102_3,
            'start_date': '2026-12-05',
            'end_date': '2026-12-20',
            'hours_used': 20
        }, follow_redirects=True)
        assert "Cannot assign" in res_mixer.data.decode('utf-8') and "Retired" in res_mixer.data.decode('utf-8')

        print("  Result: PASS - Equipment under Maintenance and Retired rejected from assignment.")
        results.append(('TEST-RES-05', 'Equipment Status Maintenance/Retired Guard', 'PASS', 'Blocked assignment of equipment under maintenance or retired'))

        # -------------------------------------------------------------
        # TEST-RES-06: Equipment Overlapping Booking Guard
        # -------------------------------------------------------------
        print("\n[TEST-RES-06] Testing Equipment Overlapping Booking Guard...")
        # Tower Crane is assigned to P102 from 2026-08-10 to 2026-09-10.
        # Attempt to assign Tower Crane to pt_102_2 from 2026-08-20 to 2026-09-05. Overlaps!
        res_eq_overlap = client.post(f'/equipment/{eq_crane_id}/assign', data={
            'project_task_id': pt_102_2,
            'start_date': '2026-08-20',
            'end_date': '2026-09-05',
            'hours_used': 30
        }, follow_redirects=True)
        assert "already assigned during the specified overlapping period" in res_eq_overlap.data.decode('utf-8')
        print("  Result: PASS - Equipment overlapping schedule collision detected and blocked.")
        results.append(('TEST-RES-06', 'Equipment Overlapping Booking Collision Guard', 'PASS', 'Overlapping equipment assignment rejected'))

        # -------------------------------------------------------------
        # TEST-RES-07: Equipment Historical Rate Snapshot Immutability
        # -------------------------------------------------------------
        print("\n[TEST-RES-07] Testing Equipment Rate Snapshot Immutability...")
        eq_rec = db.session.execute(text("""
            SELECT ea.locked_hourly_rate, ea.hours_used, e.hourly_rate 
            FROM equipment_assignments ea
            JOIN equipment e ON ea.equipment_id = e.equipment_id
            WHERE e.equipment_id = :id LIMIT 1
        """), {'id': eq_crane_id}).fetchone()
        orig_eq_rate = float(eq_rec.locked_hourly_rate)

        # Mutate catalog equipment rate to ₹5,000/hr
        client.post(f'/equipment/{eq_crane_id}/edit', data={
            'equipment_name': 'QA-Equip-Tower Crane 01',
            'equipment_type': 'Crane',
            'status': 'Available',
            'hourly_rate': 5000.00
        }, follow_redirects=True)

        after_eq_locked = db.session.execute(text("""
            SELECT locked_hourly_rate FROM equipment_assignments WHERE equipment_id = :id LIMIT 1
        """), {'id': eq_crane_id}).scalar()
        assert float(after_eq_locked) == orig_eq_rate, f"Equipment locked rate mutated from {orig_eq_rate} to {after_eq_locked}"

        ledger_eq_cost = db.session.execute(text("""
            SELECT amount FROM expense_ledger_view WHERE category = 'Equipment' AND description LIKE '%QA-Equip-Tower Crane%' LIMIT 1
        """)).scalar()
        expected_eq_cost = round(float(eq_rec.hours_used) * orig_eq_rate, 2)
        assert float(ledger_eq_cost) == float(expected_eq_cost)
        print(f"  Result: PASS - Equipment historical cost preserved at ₹{ledger_eq_cost} despite rate update to ₹5,000/hr.")
        results.append(('TEST-RES-07', 'Equipment Rate Snapshot Immutability', 'PASS', 'Historical equipment rate and ledger immune to catalog rate change'))

        # -------------------------------------------------------------
        # TEST-RES-08: Equipment Availability View Audit
        # -------------------------------------------------------------
        print("\n[TEST-RES-08] Auditing Equipment Availability & Overlap Logic on Completed Tasks...")
        eq_status = db.session.execute(text("""
            SELECT computed_status FROM equipment_status_view WHERE equipment_id = :id
        """), {'id': eq_crane_id}).scalar()
        print(f"  Tower Crane computed status in view: '{eq_status}' (Past assignment ended 2026-09-10, today is 2026-10-25)")
        assert eq_status == 'Available', f"Equipment not available after assignment ended! Got {eq_status}"
        print("  Result: PASS - Equipment computed status shows 'Available' when current date > assignment end_date.")
        results.append(('TEST-RES-08', 'Equipment Availability Calculation Logic', 'PASS', 'Equipment status correctly computed as Available after assignment expired'))

    print("\n" + "=" * 70)
    print("MODULE 2 RESULTS SUMMARY:")
    for code, name, outcome, notes in results:
        print(f"  [{outcome}] {code:12} : {name:40} | {notes}")
    print("=" * 70)
    return results

if __name__ == '__main__':
    run_tests()
