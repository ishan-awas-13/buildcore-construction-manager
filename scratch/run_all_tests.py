import subprocess
import sys
import os

scripts = [
    'test_materials_priority1.py',
    'test_financial_priority2.py',
    'test_resource_availability_priority3.py',
    'test_task_consistency_priority4.py',
    'test_history_protection_priority5.py'
]

scratch_dir = os.path.dirname(__file__)
python_bin = sys.executable

print("============================================================")
print("RUNNING ALL BUILDCORE PHASE 2 ARCHITECTURE CORRECTION TESTS")
print("============================================================\n")

all_passed = True
for s in scripts:
    script_path = os.path.join(scratch_dir, s)
    env = os.environ.copy()
    env['TEST_DB_NAME'] = os.environ.get('TEST_DB_NAME', 'buildcore_test')
    res = subprocess.run([python_bin, script_path], env=env)
    if res.returncode != 0:
        all_passed = False
        print(f"\n[FAIL] Test suite failed: {s}")
        break

if all_passed:
    print("\n" + "=" * 60)
    print("ALL 5 PHASE 2 PRIORITY TEST SUITES PASSED WITH ZERO ERRORS!")
    print("============================================================")
    sys.exit(0)
else:
    sys.exit(1)
