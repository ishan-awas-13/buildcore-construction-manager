import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

from app import create_app, db
from sqlalchemy import text

app = create_app()

def check_sequences():
    with app.app_context():
        # Check current database name
        curr_db = db.session.execute(text("SELECT current_database();")).scalar()
        print(f"Checking sequences on active database: '{curr_db}'")

        tables_pk = [
            ('users', 'user_id'),
            ('projects', 'project_id'),
            ('workers', 'worker_id'),
            ('materials', 'material_id'),
            ('equipment', 'equipment_id'),
            ('suppliers', 'supplier_id'),
            ('project_workers', 'project_worker_id'),
            ('task_types', 'task_type_id'),
            ('project_tasks', 'project_task_id'),
            ('task_workers', 'task_worker_id'),
            ('equipment_assignments', 'assignment_id'),
            ('material_usage', 'usage_id'),
            ('purchases', 'purchase_id'),
            ('purchase_items', 'purchase_item_id'),
            ('expenses', 'expense_id')
        ]
        
        all_ok = True
        print(f"\n{'Table.PK Column':<35} | {'Max ID':<8} | {'Seq Name':<35} | {'Last Val':<9} | {'Status'}")
        print("-" * 105)
        for table, pk in tables_pk:
            max_id = db.session.execute(text(f"SELECT MAX({pk}) FROM {table}")).scalar() or 0
            seq_query = text("SELECT pg_get_serial_sequence(:t, :pk)")
            seq_name = db.session.execute(seq_query, {'t': table, 'pk': pk}).scalar()
            
            if seq_name:
                curr_val = db.session.execute(text(f"SELECT last_value, is_called FROM {seq_name}")).fetchone()
                last_val = curr_val[0]
                is_called = curr_val[1]
                
                # If is_called is True, nextval() will return last_val + 1. If last_val < max_id, collision occurs!
                # If is_called is False, nextval() will return last_val. If last_val <= max_id, collision occurs!
                next_val = (last_val + 1) if is_called else last_val
                if next_val <= max_id:
                    status = f"COLLISION RISK! (Next val {next_val} <= Max {max_id})"
                    all_ok = False
                else:
                    status = f"HEALTHY (Next val {next_val} > Max {max_id})"
                    
                print(f"{f'{table}.{pk}':<35} | {max_id:<8} | {seq_name:<35} | {last_val:<9} | {status}")
            else:
                print(f"{f'{table}.{pk}':<35} | {max_id:<8} | {'NO SEQUENCE!':<35} | {'N/A':<9} | WARNING")
                all_ok = False
                
        print("\n=== SEQUENCE AUDIT RESULT ===")
        if all_ok:
            print("All sequences are properly aligned. Inserts will not produce duplicate key errors.")
        else:
            print("WARNING: One or more sequences need to be synchronized with setval()!")

if __name__ == '__main__':
    check_sequences()
