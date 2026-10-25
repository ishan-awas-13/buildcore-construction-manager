import glob
import os

for root in [
    r'c:\Users\ishan\OneDrive\Desktop\College_Files\SEM-5\Database Systems\BuildCore_DB_Project_Corrected',
    r'c:\Users\ishan\OneDrive\Desktop\College_Files\SEM-5\Database Systems\BuildCore_DB_Project'
]:
    for p in glob.glob(os.path.join(root, 'scratch', 'test_*.py')):
        with open(p, 'r', encoding='utf-8') as f:
            s = f.read()
        s = s.replace("assert curr_db == 'buildcore_copy'", "assert curr_db in ('buildcore_copy', 'buildcore_test')")
        s = s.replace("assert active_db == 'buildcore_copy'", "assert active_db in ('buildcore_copy', 'buildcore_test')")
        with open(p, 'w', encoding='utf-8') as f:
            f.write(s)
        print('Updated assertions in:', p)
