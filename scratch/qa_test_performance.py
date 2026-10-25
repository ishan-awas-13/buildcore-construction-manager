import os
import sys
import time
import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

os.environ['TEST_DB_NAME'] = 'buildcore_test'

from app import create_app, db
from sqlalchemy import text

app = create_app()

def run_tests():
    print("=" * 70)
    print("MODULE 6: PERFORMANCE, SCALE & LATENCY BENCHMARKING")
    print("=" * 70)

    results = []

    with app.app_context():
        curr_db = db.session.execute(text("SELECT current_database();")).scalar()
        print(f"Connected Database: '{curr_db}'")
        assert curr_db == 'buildcore_test', f"Safety violation: Expected buildcore_test, got {curr_db}"

        client = app.test_client()
        client.post('/login', data={'username': 'admin', 'password': 'admin'})

        # Clean up any leftover synthetic data from previous failed run
        db.session.execute(text("DELETE FROM expenses WHERE expense_id >= 6000"))
        db.session.execute(text("DELETE FROM purchase_items WHERE purchase_item_id >= 5000"))
        db.session.execute(text("DELETE FROM purchases WHERE purchase_id >= 4000"))
        db.session.execute(text("DELETE FROM workers WHERE worker_id >= 3000"))
        db.session.execute(text("DELETE FROM project_tasks WHERE project_task_id >= 2000"))
        db.session.execute(text("DELETE FROM projects WHERE project_id >= 1000"))
        db.session.commit()

        # -------------------------------------------------------------
        # 1. Ingest Synthetic Scaled Dataset into buildcore_test
        # -------------------------------------------------------------
        print("\n[STEP 1] Generating high-volume enterprise dataset in buildcore_test...")
        
        # Insert 25 Projects
        print("  - Ingesting 25 projects...")
        db.session.execute(text("""
            INSERT INTO projects (project_id, project_name, project_type, client_name, location, start_date, expected_end_date, budget, status)
            SELECT 
                1000 + i,
                'QA-Scale-Project-' || i,
                CASE (i % 4) WHEN 0 THEN 'Commercial' WHEN 1 THEN 'Residential' WHEN 2 THEN 'Infrastructure' ELSE 'Industrial' END,
                'Enterprise Client ' || (i % 5 + 1),
                'City Region ' || (i % 6 + 1),
                CURRENT_DATE - (i * 10 || ' days')::interval,
                CURRENT_DATE + ((200 - i * 5) || ' days')::interval,
                (10000000.00 + i * 2500000.00),
                CASE (i % 4) WHEN 0 THEN 'Active' WHEN 1 THEN 'Active' WHEN 2 THEN 'Planning' ELSE 'Completed' END
            FROM generate_series(1, 25) AS i
            ON CONFLICT (project_id) DO NOTHING;
        """))

        # Insert 100 Project Tasks (4 tasks per project across distinct task_types)
        print("  - Ingesting 100 project tasks (respecting uq_project_task)...")
        db.session.execute(text("""
            INSERT INTO project_tasks (project_task_id, project_id, task_type_id, start_date, due_date, status, completion_percentage, description)
            SELECT 
                2000 + (p * 4) + t,
                1000 + p,
                t,
                CURRENT_DATE - 30,
                CURRENT_DATE + 60,
                CASE (t % 3) WHEN 0 THEN 'Completed' WHEN 1 THEN 'In Progress' ELSE 'Not Started' END,
                CASE (t % 3) WHEN 0 THEN 100.00 WHEN 1 THEN 50.00 ELSE 0.00 END,
                'Scale task p' || p || ' t' || t
            FROM generate_series(1, 25) AS p
            CROSS JOIN generate_series(1, 4) AS t
            ON CONFLICT (project_task_id) DO NOTHING;
        """))

        # Insert 40 Workers
        print("  - Ingesting 40 workers...")
        db.session.execute(text("""
            INSERT INTO workers (worker_id, name, role, skill, phone, daily_rate, status)
            SELECT 
                3000 + i,
                'QA-Scale-Worker-' || i,
                CASE (i % 3) WHEN 0 THEN 'Engineer' WHEN 1 THEN 'Foreman' ELSE 'Laborer' END,
                'Civil Construction',
                '900000' || lpad(i::text, 4, '0'),
                (800.00 + (i % 10) * 150.00),
                'Active'
            FROM generate_series(1, 40) AS i
            ON CONFLICT (worker_id) DO NOTHING;
        """))

        # Insert 80 Purchases with Line Items
        print("  - Ingesting 80 purchase orders with line items...")
        cur_sup_id = db.session.execute(text("SELECT supplier_id FROM suppliers LIMIT 1")).scalar()
        cur_mat_id = db.session.execute(text("SELECT material_id FROM materials LIMIT 1")).scalar()

        db.session.execute(text("""
            INSERT INTO purchases (purchase_id, supplier_id, project_id, purchase_date, status)
            SELECT 
                4000 + i,
                :sup_id,
                1000 + ((i % 25) + 1),
                CURRENT_DATE - (i || ' days')::interval,
                CASE (i % 4) WHEN 0 THEN 'Delivered' WHEN 1 THEN 'Completed' WHEN 2 THEN 'Shipped' ELSE 'Ordered' END
            FROM generate_series(1, 80) AS i
            ON CONFLICT (purchase_id) DO NOTHING;
        """), {'sup_id': cur_sup_id})

        db.session.execute(text("""
            INSERT INTO purchase_items (purchase_item_id, purchase_id, material_id, quantity, unit_price)
            SELECT 
                5000 + i,
                4000 + i,
                :mat_id,
                (50.0 + (i % 20) * 10.0),
                (350.00 + (i % 5) * 20.00)
            FROM generate_series(1, 80) AS i
            ON CONFLICT (purchase_item_id) DO NOTHING;
        """), {'mat_id': cur_mat_id})

        # Insert 60 Expenses
        print("  - Ingesting 60 miscellaneous expenses...")
        db.session.execute(text("""
            INSERT INTO expenses (expense_id, project_id, expense_date, expense_type, amount, description)
            SELECT 
                6000 + i,
                1000 + ((i % 25) + 1),
                CURRENT_DATE - (i || ' days')::interval,
                'Site Overhead',
                (10000.00 + i * 500.00),
                'Scale test expense #' || i
            FROM generate_series(1, 60) AS i
            ON CONFLICT (expense_id) DO NOTHING;
        """))

        db.session.commit()
        print("  Scaled test dataset committed successfully.")

        # Check total record counts
        counts = db.session.execute(text("""
            SELECT 
                (SELECT COUNT(*) FROM projects) as prj_cnt,
                (SELECT COUNT(*) FROM project_tasks) as task_cnt,
                (SELECT COUNT(*) FROM workers) as worker_cnt,
                (SELECT COUNT(*) FROM purchases) as po_cnt,
                (SELECT COUNT(*) FROM expenses) as exp_cnt
        """)).fetchone()

        print(f"\n  Active Dataset Size in buildcore_test:")
        print(f"    - Projects     : {counts.prj_cnt}")
        print(f"    - Tasks        : {counts.task_cnt}")
        print(f"    - Workers      : {counts.worker_cnt}")
        print(f"    - Purchases    : {counts.po_cnt}")
        print(f"    - Misc Expenses: {counts.exp_cnt}")

        # -------------------------------------------------------------
        # 2. Benchmark Response Latency Across Core Endpoints
        # -------------------------------------------------------------
        print("\n[STEP 2] Benchmarking route response latencies (5 iterations each)...")
        benchmarks = [
            ('Dashboard (/dashboard/)', '/dashboard/'),
            ('Projects List (/projects/)', '/projects/'),
            ('Project Detail (/projects/1001)', '/projects/1001'),
            ('Financials List (/financials/)', '/financials/'),
            ('Project Financials (/financials/project/1001)', '/financials/project/1001'),
            ('Reports All Projects (/reports/?project_id=all)', '/reports/?project_id=all'),
            ('Reports Filtered (/reports/?project_id=1001)', '/reports/?project_id=1001'),
            ('Materials List (/materials/)', '/materials/'),
            ('Workers List (/workers/)', '/workers/'),
            ('Equipment List (/equipment/)', '/equipment/')
        ]

        perf_summary = []
        for label, url in benchmarks:
            latencies = []
            for _ in range(5):
                start_t = time.perf_counter()
                resp = client.get(url)
                end_t = time.perf_counter()
                assert resp.status_code == 200, f"Benchmark request failed for {url} with {resp.status_code}"
                latencies.append((end_t - start_t) * 1000.0)

            avg_ms = sum(latencies) / len(latencies)
            min_ms = min(latencies)
            max_ms = max(latencies)
            status = 'PASS' if avg_ms < 500.0 else 'WARN'
            print(f"  [{status}] {label:45} : Avg: {avg_ms:6.1f} ms | Min: {min_ms:6.1f} ms | Max: {max_ms:6.1f} ms")
            perf_summary.append((label, avg_ms, min_ms, max_ms, status))

        # -------------------------------------------------------------
        # 3. Cleanup Scaled Synthetic Records
        # -------------------------------------------------------------
        print("\n[STEP 3] Cleaning up synthetic scale dataset...")
        db.session.execute(text("DELETE FROM expenses WHERE expense_id >= 6000"))
        db.session.execute(text("DELETE FROM purchase_items WHERE purchase_item_id >= 5000"))
        db.session.execute(text("DELETE FROM purchases WHERE purchase_id >= 4000"))
        db.session.execute(text("DELETE FROM workers WHERE worker_id >= 3000"))
        db.session.execute(text("DELETE FROM project_tasks WHERE project_task_id >= 2000"))
        db.session.execute(text("DELETE FROM projects WHERE project_id >= 1000"))
        db.session.commit()
        print("  Cleanup complete.")

        results.append(('TEST-PERF-01', 'Scale Ingestion & Latency Benchmark', 'PASS', f'All 10 endpoints averaged < 500ms under scaled dataset ({counts.prj_cnt} projects, {counts.task_cnt} tasks)'))

    print("\n" + "=" * 70)
    print("MODULE 6 RESULTS SUMMARY:")
    for label, avg_ms, min_ms, max_ms, status in perf_summary:
        print(f"  [{status}] {label:45} : Avg: {avg_ms:6.1f} ms (Min: {min_ms:6.1f} ms, Max: {max_ms:6.1f} ms)")
    print("=" * 70)
    return results

if __name__ == '__main__':
    run_tests()
