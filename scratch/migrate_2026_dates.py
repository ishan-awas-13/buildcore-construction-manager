import os
import sys
from datetime import date
from sqlalchemy import create_engine, text

def run_migration_for_db(db_name):
    print(f"\n=======================================================")
    print(f"MIGRATING DATABASE: {db_name} TO 26 OCTOBER 2026 TIMELINE")
    print(f"=======================================================")
    
    engine = create_engine(f"postgresql+psycopg2://postgres:admin123@127.0.0.1:5432/{db_name}")
    
    with engine.begin() as conn:
        print("1. Updating Views...")
        conn.execute(text("""
            CREATE OR REPLACE VIEW worker_status_view AS
            SELECT w.*,
                CASE 
                    WHEN w.status IN ('On Leave', 'Inactive') THEN w.status
                    WHEN EXISTS (
                        SELECT 1 FROM task_workers tw
                        JOIN project_tasks pt ON tw.project_task_id = pt.project_task_id
                        WHERE tw.worker_id = w.worker_id 
                          AND pt.status IN ('In Progress', 'Not Started')
                          AND (pt.due_date IS NULL OR pt.due_date >= CURRENT_DATE)
                    ) THEN 'Assigned'
                    ELSE 'Available'
                END AS computed_status
            FROM workers w;
        """))

        conn.execute(text("""
            CREATE OR REPLACE VIEW equipment_status_view AS
            SELECT e.*,
                CASE 
                    WHEN e.status IN ('Maintenance', 'Retired') THEN e.status
                    WHEN EXISTS (
                        SELECT 1 FROM equipment_assignments ea
                        JOIN project_tasks pt ON ea.project_task_id = pt.project_task_id
                        WHERE ea.equipment_id = e.equipment_id
                        AND ea.start_date <= CURRENT_DATE 
                        AND (
                            (ea.end_date IS NOT NULL AND ea.end_date >= CURRENT_DATE)
                            OR (ea.end_date IS NULL AND pt.status != 'Completed' AND (pt.due_date IS NULL OR pt.due_date >= CURRENT_DATE))
                        )
                    ) THEN 'In Use'
                    ELSE 'Available'
                END AS computed_status
            FROM equipment e;
        """))

        print("2. Updating Projects...")
        projects_updates = [
            (1, '2025-06-01', '2027-12-31', 'Active'),
            (2, '2024-05-10', '2026-08-31', 'Completed'),
            (3, '2025-08-01', '2027-08-31', 'Active'),
            (4, '2024-02-15', '2027-06-30', 'Delayed'),
            (5, '2025-04-01', '2027-06-30', 'Active'),
            (6, '2026-01-01', '2028-12-31', 'Active'),
            (7, '2024-01-15', '2026-06-30', 'Completed'),
            (8, '2023-01-10', '2024-12-15', 'Completed')
        ]
        for p_id, s_date, e_date, status in projects_updates:
            conn.execute(text("""
                UPDATE projects 
                SET start_date = :s, expected_end_date = :e, status = :st
                WHERE project_id = :id
            """), {'s': s_date, 'e': e_date, 'st': status, 'id': p_id})

        print("3. Updating Tasks...")
        task_updates = [
            # Project 1: Navi Mumbai Airport (Active)
            (1, '2025-06-01', '2025-08-31', 'Completed', 100.00),
            (2, '2025-09-01', '2026-03-31', 'Completed', 100.00),
            (3, '2026-11-01', '2027-06-30', 'Not Started', 0.00),
            (4, '2026-04-01', '2026-12-31', 'In Progress', 65.00),
            # Project 2: Delhi-Mumbai Expressway (Completed)
            (5, '2024-05-10', '2024-08-31', 'Completed', 100.00),
            (6, '2024-09-01', '2025-03-31', 'Completed', 100.00),
            (7, '2025-04-01', '2026-08-31', 'Completed', 100.00),
            # Project 3: Cyber City IT Park (Active)
            (8, '2025-08-01', '2025-10-31', 'Completed', 100.00),
            (9, '2025-11-01', '2026-04-30', 'Completed', 100.00),
            (10, '2026-05-01', '2026-09-30', 'Completed', 100.00),
            (11, '2026-10-01', '2027-04-30', 'In Progress', 20.00),
            (12, '2026-07-01', '2026-11-30', 'In Progress', 75.00),
            # Project 4: Ganga River Bridge (Delayed)
            (13, '2024-02-15', '2024-05-31', 'Completed', 100.00),
            (14, '2024-06-01', '2025-09-30', 'Completed', 100.00),
            (15, '2025-10-01', '2027-03-31', 'In Progress', 45.00),
            # Project 5: Prestige Sunrise Apartments (Active)
            (16, '2025-04-01', '2025-10-31', 'Completed', 100.00),
            (17, '2025-11-01', '2026-05-31', 'Completed', 100.00),
            (18, '2026-06-01', '2026-11-30', 'In Progress', 65.00),
            (19, '2026-08-01', '2026-12-31', 'In Progress', 40.00),
            (20, '2027-01-01', '2027-05-31', 'Not Started', 0.00),
            (21, '2026-09-15', '2027-01-31', 'In Progress', 25.00),
            # Project 7: Tata Steel Plant Expansion (Completed)
            (22, '2024-01-15', '2024-04-30', 'Completed', 100.00),
            (23, '2024-05-01', '2024-11-30', 'Completed', 100.00),
            (24, '2024-12-01', '2025-09-30', 'Completed', 100.00),
            (25, '2025-10-01', '2026-06-30', 'Completed', 100.00),
            # Project 8: Heritage Museum Renovation (Completed)
            (26, '2023-01-10', '2023-09-30', 'Completed', 100.00),
            (27, '2023-10-01', '2024-05-31', 'Completed', 100.00),
            (28, '2023-06-01', '2024-02-28', 'Completed', 100.00),
            (29, '2023-08-01', '2024-04-30', 'Completed', 100.00),
        ]
        for pt_id, s_date, e_date, st, pct in task_updates:
            conn.execute(text("""
                UPDATE project_tasks
                SET start_date = :s, due_date = :e, status = :st, completion_percentage = :pct
                WHERE project_task_id = :id
            """), {'s': s_date, 'e': e_date, 'st': st, 'pct': pct, 'id': pt_id})

        # Auto-complete any remaining tasks whose due_date < CURRENT_DATE
        conn.execute(text("""
            UPDATE project_tasks
            SET status = 'Completed', completion_percentage = 100.00
            WHERE due_date < CURRENT_DATE AND status != 'Completed'
        """))

        print("4. Updating Equipment Assignments...")
        ea_updates = [
            (1, '2025-09-15', '2026-03-31'), # Potain Crane on pt 2 (Completed)
            (2, '2024-09-15', '2025-03-31'), # Excavator on pt 6 (Completed)
            (3, '2025-05-01', '2026-08-31'), # Dump truck on pt 7 (Completed)
            (4, '2025-11-20', '2026-04-30'), # Mixer on pt 9 (Completed)
            (5, '2025-12-15', '2026-05-31'), # Generator on pt 17 (Completed)
            (6, '2024-02-01', '2024-04-30'), # Hydra crane on pt 22 (Completed)
        ]
        for ea_id, s_date, e_date in ea_updates:
            conn.execute(text("""
                UPDATE equipment_assignments
                SET start_date = :s, end_date = :e
                WHERE assignment_id = :id
            """), {'s': s_date, 'e': e_date, 'id': ea_id})

        # Fix or remove stale test tractor assignment on Cyber City task 11:
        # Task 11 is now 2026-10-01 to 2027-04-30. If tractor was assigned, update dates to current active period
        conn.execute(text("""
            UPDATE equipment_assignments
            SET start_date = '2026-10-15', end_date = '2026-11-15', hours_used = 15.0
            WHERE assignment_id = 16
        """))

        # Release any open-ended equipment assignments on completed tasks:
        conn.execute(text("""
            UPDATE equipment_assignments ea
            SET end_date = pt.due_date
            FROM project_tasks pt
            WHERE ea.project_task_id = pt.project_task_id
              AND ea.end_date IS NULL
              AND pt.status = 'Completed'
        """))

        print("5. Updating Purchases & Expenses...")
        conn.execute(text("""
            UPDATE purchases SET purchase_date = '2025-09-15' WHERE purchase_id = 1;
            UPDATE purchases SET purchase_date = '2025-06-20' WHERE purchase_id = 2;
            UPDATE purchases SET purchase_date = '2024-06-05' WHERE purchase_id = 3;
            UPDATE purchases SET purchase_date = '2023-08-20' WHERE purchase_id = 4;
            UPDATE purchases SET purchase_date = '2026-03-01' WHERE purchase_id = 5;
            UPDATE purchases SET purchase_date = '2025-11-10' WHERE purchase_id = 6;
            UPDATE purchases SET purchase_date = '2024-02-20' WHERE purchase_id = 7;
        """))

        conn.execute(text("""
            UPDATE expenses SET expense_date = '2026-08-31' WHERE expense_id = 1;
            UPDATE expenses SET expense_date = '2026-08-31' WHERE expense_id = 2;
            UPDATE expenses SET expense_date = '2025-12-31' WHERE expense_id = 3;
            UPDATE expenses SET expense_date = '2025-08-15' WHERE expense_id = 4;
            UPDATE expenses SET expense_date = '2026-07-31' WHERE expense_id = 5;
            UPDATE expenses SET expense_date = '2024-05-30' WHERE expense_id = 6;
        """))

        print(f"--> Successfully migrated {db_name}!")

if __name__ == '__main__':
    for db_target in ['buildcore_copy', 'buildcore', 'buildcore_test']:
        try:
            run_migration_for_db(db_target)
        except Exception as e:
            print(f"Error on {db_target}: {e}")
