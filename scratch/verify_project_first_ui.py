import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ['TEST_DB_NAME'] = 'buildcore_test'

from app import create_app, db
from sqlalchemy import text

app = create_app()

def test_project_first_architecture():
    print("=" * 70)
    print("VERIFYING PROJECT-FIRST ARCHITECTURE WORKSPACE & REGISTERS")
    print("=" * 70)

    with app.app_context():
        client = app.test_client()
        # Login
        client.post('/login', data={'username': 'admin', 'password': 'admin'})

        # 1. Projects listing with status filters
        print("\n[1] Testing Projects list and status filters...")
        filters = ['', '?status=Active', '?status=Planned', '?status=On Hold', '?status=Completed']
        for q in filters:
            url = f"/projects/{q}"
            resp = client.get(url)
            assert resp.status_code == 200, f"Failed for {url} with {resp.status_code}"
            assert b"Company Projects" in resp.data
        print("  --> PASS: All project filter variations rendered HTTP 200.")

        # 2. Project Workspace Tabs on Project 1
        print("\n[2] Testing 7 Workspace Tabs on Project 1...")
        tabs = [
            ('/projects/1', [b"Workspace Overview", b"Spend vs Budget", b"Project Details"]),
            ('/projects/1/tasks', [b"Project Tasks", b"Add Task"]),
            ('/projects/1/workers', [b"Assigned Project Workers", b"Assign Worker"]),
            ('/projects/1/equipment', [b"Assigned Project Equipment", b"Assign Equipment"]),
            ('/projects/1/materials', [b"Project Materials & Inventory", b"Allocate Material"]),
            ('/projects/1/purchases', [b"Project Purchase Orders", b"New Purchase Order"]),
            ('/projects/1/financials', [b"Project Financial Ledger", b"Add Misc Expense"])
        ]

        for url, expected_phrases in tabs:
            resp = client.get(url)
            assert resp.status_code == 200, f"Failed for {url} with status {resp.status_code}"
            for phrase in expected_phrases:
                assert phrase in resp.data, f"Missing phrase '{phrase.decode()}' in {url}"
            assert b"nav-tabs" in resp.data
            print(f"  --> PASS: {url} rendered tab cleanly with navigation bar.")

        # 3. Legacy 302 Redirection
        print("\n[3] Testing Legacy URL Redirection...")
        resp_leg = client.get('/financials/project/1')
        assert resp_leg.status_code == 302, f"Expected 302 for /financials/project/1, got {resp_leg.status_code}"
        assert '/projects/1/financials' in resp_leg.headers['Location']
        print("  --> PASS: /financials/project/1 correctly redirects (302) to /projects/1/financials.")

        # 4. Company Registers (Read-Mostly with Current Deployment)
        print("\n[4] Testing Company Registers...")
        registers = [
            ('/workers/', b"Workers Register"),
            ('/workers/1', b"Current Deployment"),
            ('/equipment/', b"Equipment Register"),
            ('/equipment/1', b"Current Deployment"),
            ('/materials/', b"Materials Register"),
            ('/tasks/', b"Task Types Register"),
            ('/suppliers/', b"Suppliers Register")
        ]
        for url, phrase in registers:
            resp = client.get(url)
            assert resp.status_code == 200, f"Failed for {url} with {resp.status_code}"
            assert phrase in resp.data, f"Missing phrase '{phrase.decode()}' in {url}"
            print(f"  --> PASS: Register {url} rendered with expected heading/deployment info.")

        # 5. Purchase Creation with pre-selected Project
        print("\n[5] Testing Pre-selected Project on New Purchase Order...")
        resp_po = client.get('/purchases/add?project_id=1')
        assert resp_po.status_code == 200
        assert b"Create Purchase Order" in resp_po.data
        assert b"Back to Project Purchases" in resp_po.data
        print("  --> PASS: Purchase order form supports ?project_id=1 and provides return workspace link.")

    print("\n" + "=" * 70)
    print("ALL PROJECT-FIRST ARCHITECTURE WORKSPACE & REGISTER CHECKS PASSED 100%!")
    print("=" * 70)

if __name__ == '__main__':
    test_project_first_architecture()
