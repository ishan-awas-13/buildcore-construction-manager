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
    print("MODULE 5: ADVERSARIAL SECURITY, ROUTING & UI ERROR HANDLING TESTS")
    print("=" * 70)

    results = []

    with app.app_context():
        curr_db = db.session.execute(text("SELECT current_database();")).scalar()
        print(f"Connected Database: '{curr_db}'")
        assert curr_db == 'buildcore_test', f"Safety violation: Expected buildcore_test, got {curr_db}"

        # -------------------------------------------------------------
        # TEST-SEC-01: Unauthenticated Access Guard Across All Endpoints
        # -------------------------------------------------------------
        print("\n[TEST-SEC-01] Testing Unauthenticated Access Protection...")
        unauth_client = app.test_client()

        protected_endpoints = [
            '/dashboard/',
            '/projects/',
            '/projects/new',
            '/workers/',
            '/workers/new',
            '/equipment/',
            '/equipment/new',
            '/materials/',
            '/materials/new',
            '/suppliers/',
            '/suppliers/add',
            '/purchases/',
            '/purchases/add',
            '/financials/',
            '/reports/'
        ]

        all_redirected = True
        for ep in protected_endpoints:
            res = unauth_client.get(ep)
            if res.status_code != 302 or '/login' not in (res.headers.get('Location') or ''):
                all_redirected = False
                print(f"  ENDPOINT BREACH / EXPOSED: {ep} returned status {res.status_code}")

        assert all_redirected, "One or more protected endpoints allowed unauthenticated access!"
        print(f"  Result: PASS - All {len(protected_endpoints)} protected endpoints securely redirect to /login.")
        results.append(('TEST-SEC-01', 'Unauthenticated Access Protection', 'PASS', f'All {len(protected_endpoints)} endpoints guarded by login_required'))

        # -------------------------------------------------------------
        # TEST-SEC-02: Non-Existent Record Navigation (404/Crash Guard)
        # -------------------------------------------------------------
        print("\n[TEST-SEC-02] Testing Graceful Recovery on Non-Existent IDs...")
        auth_client = app.test_client()
        auth_client.post('/login', data={'username': 'admin', 'password': 'admin'})

        non_existent_targets = [
            ('/projects/999999', 'Project not found'),
            ('/workers/999999', 'Worker not found'),
            ('/equipment/999999', 'Equipment not found'),
            ('/materials/999999', 'Material not found'),
            ('/purchases/999999', 'Purchase order not found'),
            ('/tasks/999999', 'Task type not found'),
            ('/financials/project/999999', 'Project not found')
        ]

        all_handled_cleanly = True
        for url, expected_flash in non_existent_targets:
            res = auth_client.get(url, follow_redirects=True)
            if res.status_code == 500:
                all_handled_cleanly = False
                print(f"  CRASH: {url} threw unhandled HTTP 500!")
            else:
                html = res.data.decode('utf-8')
                if expected_flash not in html:
                    all_handled_cleanly = False
                    print(f"  MISSED FLASH: {url} did not show '{expected_flash}'")

        assert all_handled_cleanly, "One or more non-existent records caused HTTP 500 or missed flash error!"
        print(f"  Result: PASS - All {len(non_existent_targets)} non-existent routes recovered gracefully without crashing.")
        results.append(('TEST-SEC-02', 'Non-Existent Record Graceful Recovery', 'PASS', f'All {len(non_existent_targets)} invalid IDs redirected with flash'))

        # -------------------------------------------------------------
        # TEST-SEC-03: Negative Budget Submission in Project Creation
        # -------------------------------------------------------------
        print("\n[TEST-SEC-03] Testing Negative Budget Submission in Project Form...")
        res_neg_budget = auth_client.post('/projects/new', data={
            'project_name': 'QA-Negative-Budget-Test',
            'project_type': 'Commercial',
            'client_name': 'Test Client',
            'location': 'Test Location',
            'start_date': '2026-11-01',
            'expected_end_date': '2027-05-01',
            'budget': -50000.00,
            'status': 'Planning'
        }, follow_redirects=True)
        
        html = res_neg_budget.data.decode('utf-8')
        assert "cannot be negative" in html or "Invalid budget" in html
        print("  Result: PASS - Negative budget form validation blocked submission.")
        results.append(('TEST-SEC-03', 'Negative Project Budget Validation', 'PASS', 'Validation rejected negative budget'))

        # -------------------------------------------------------------
        # TEST-UI-01: Character Encoding & Corrupted Symbol Inspection
        # -------------------------------------------------------------
        print("\n[TEST-UI-01] Testing Template Character Encoding & Symbol Corruption...")
        dash_html = auth_client.get('/dashboard/').data.decode('utf-8')
        
        # Check for corrupted encoding artifact ",1"
        assert ",1" not in dash_html, "Dashboard still contains corrupted ',1' encoding artifact!"
        assert "₹" in dash_html, "Dashboard missing expected Rupee symbol (₹)!"
        print("  Result: PASS - Dashboard properly displays Rupee symbols without corrupt encoding.")
        results.append(('TEST-UI-01', 'Template Currency Glyph Encoding', 'PASS', 'Properly formatted currency glyphs (₹) verified'))

    print("\n" + "=" * 70)
    print("MODULE 5 RESULTS SUMMARY:")
    for code, name, outcome, notes in results:
        print(f"  [{outcome}] {code:12} : {name:40} | {notes}")
    print("=" * 70)
    return results

if __name__ == '__main__':
    run_tests()
