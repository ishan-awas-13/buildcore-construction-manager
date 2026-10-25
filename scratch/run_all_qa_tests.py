import subprocess
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

scratch_dir = os.path.dirname(__file__)
python_bin = sys.executable

qa_suites = [
    ('Enterprise Data Simulation', 'qa_simulate_enterprise.py'),
    ('Module 1: Materials Isolation', 'qa_test_materials.py'),
    ('Module 2: Resource Availability', 'qa_test_resources.py'),
    ('Module 3: Financial Integrity', 'qa_test_financials.py'),
    ('Module 4: Project & Task Lifecycle', 'qa_test_tasks_projects.py'),
    ('Module 5: Security & UI Handling', 'qa_test_security_ui.py'),
    ('Module 6: Performance & Scalability', 'qa_test_performance.py'),
    ('Module 7: Phase 2 Foundational Regression', 'run_all_tests.py'),
    ('Module 8: Project-First Workspace & Registers', 'verify_project_first_ui.py')
]

print("=" * 75)
print("BUILDCORE MASTER QA & ADVERSARIAL REGRESSION SUITE")
print("=" * 75)

suite_results = []
all_passed = True

for title, script in qa_suites:
    print(f"\n>>> EXECUTING: {title} ({script})...")
    script_path = os.path.join(scratch_dir, script)
    env = os.environ.copy()
    env['TEST_DB_NAME'] = 'buildcore_test'
    res = subprocess.run([python_bin, script_path], env=env)
    
    if res.returncode == 0:
        suite_results.append((title, 'PASS'))
        print(f">>> [SUCCESS] {title} passed.")
    else:
        suite_results.append((title, 'FAIL'))
        print(f">>> [FAILURE] {title} failed with exit code {res.returncode}.")
        all_passed = False
        break

print("\n" + "=" * 75)
print("MASTER QA TEST EXECUTION SUMMARY:")
for title, status in suite_results:
    print(f"  [{status}] {title:50}")
print("=" * 75)

if all_passed:
    print("\nALL ADVERSARIAL QA MODULES AND REGRESSION SUITES PASSED 100%!")
    sys.exit(0)
else:
    print("\nMASTER QA SUITE DETECTED FAILURES.")
    sys.exit(1)
