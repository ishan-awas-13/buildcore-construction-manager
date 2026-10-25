import os
import sys
import psycopg2
from datetime import date

sys.stdout.reconfigure(encoding='utf-8')

DB_NAME = "buildcore_test"
DB_USER = "postgres"
DB_PASSWORD = "admin123"
DB_HOST = "127.0.0.1"
DB_PORT = 5432

def simulate_enterprise():
    print("=" * 60)
    print(f"SEEDING ENTERPRISE MULTI-PROJECT SIMULATION ON '{DB_NAME}'")
    print("=" * 60)

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # Verify database safety
        cur.execute("SELECT current_database();")
        active_db = cur.fetchone()[0]
        assert active_db == 'buildcore_test', f"CRITICAL SAFETY VIOLATION: Connected to '{active_db}', expected 'buildcore_test'!"

        # -------------------------------------------------------------
        # 1. Clean up any previous test simulation records in buildcore_test
        # -------------------------------------------------------------
        print("\n[1/6] Cleaning up previous simulation records in buildcore_test...")
        cur.execute("DELETE FROM projects WHERE project_name LIKE 'QA-SIM-%';")
        cur.execute("DELETE FROM workers WHERE name LIKE 'QA-Worker-%';")
        cur.execute("DELETE FROM equipment WHERE equipment_name LIKE 'QA-Equip-%';")
        cur.execute("DELETE FROM suppliers WHERE supplier_name LIKE 'QA-Supplier-%';")
        cur.execute("DELETE FROM materials WHERE material_name LIKE 'QA-Mat-%';")
        cur.execute("DELETE FROM task_types WHERE task_name LIKE 'QA-Task-%';")

        # -------------------------------------------------------------
        # 2. Reusable Test Master Resources
        # -------------------------------------------------------------
        print("[2/6] Inserting master test resources (Suppliers, Materials, Task Types, Workers, Equipment)...")
        # Suppliers
        cur.execute("""
            INSERT INTO suppliers (supplier_name, contact_person, phone, email, address)
            VALUES 
            ('QA-Supplier-Alpha', 'Ramesh Kumar', '9876543210', 'ramesh@alpha.test', '101 Industrial Area, Mumbai'),
            ('QA-Supplier-Beta', 'Suresh Patel', '9876543211', 'suresh@beta.test', '202 Steel Yard, Pune')
            RETURNING supplier_id, supplier_name;
        """)
        sup_map = {name: sid for sid, name in cur.fetchall()}

        # Materials
        cur.execute("""
            INSERT INTO materials (material_name, unit, unit_cost)
            VALUES 
            ('QA-Mat-Cement OPC 53', 'Bags', 380.00),
            ('QA-Mat-TMT Steel Fe500', 'Tonnes', 55000.00),
            ('QA-Mat-ReadyMix Concrete M30', 'cu.m', 4500.00),
            ('QA-Mat-River Sand', 'Tonnes', 1800.00)
            RETURNING material_id, material_name;
        """)
        mat_map = {name: mid for mid, name in cur.fetchall()}

        # Task Types
        cur.execute("""
            INSERT INTO task_types (task_name, description)
            VALUES 
            ('QA-Task-Site Survey', 'Geotechnical and contour survey'),
            ('QA-Task-Piling Work', 'Drilling and casting cast-in-situ piles'),
            ('QA-Task-Superstructure', 'RCC column and beam casting'),
            ('QA-Task-Finishing', 'Plastering, painting, and architectural handover')
            RETURNING task_type_id, task_name;
        """)
        tt_map = {name: tid for tid, name in cur.fetchall()}

        # Workers
        cur.execute("""
            INSERT INTO workers (name, role, skill, phone, daily_rate, status)
            VALUES 
            ('QA-Worker-Anil (Site Eng)', 'Engineer', 'Civil Engineering', '9123456780', 1800.00, 'Active'),
            ('QA-Worker-Bikram (Foreman)', 'Foreman', 'Masonry & Concrete', '9123456781', 1200.00, 'Active'),
            ('QA-Worker-Chetan (Mason)', 'Laborer', 'Masonry', '9123456782', 800.00, 'Active'),
            ('QA-Worker-Deepak (OnLeave)', 'Laborer', 'Carpentry', '9123456783', 750.00, 'On Leave'),
            ('QA-Worker-Eshwar (Inactive)', 'Laborer', 'Bar Bending', '9123456784', 850.00, 'Inactive')
            RETURNING worker_id, name;
        """)
        worker_map = {name: wid for wid, name in cur.fetchall()}

        # Equipment
        cur.execute("""
            INSERT INTO equipment (equipment_name, equipment_type, status, hourly_rate)
            VALUES 
            ('QA-Equip-Tower Crane 01', 'Crane', 'Available', 2500.00),
            ('QA-Equip-Concrete Pump 01', 'Pump', 'Available', 1500.00),
            ('QA-Equip-JCB Excavator 01', 'Earthmover', 'Maintenance', 1800.00),
            ('QA-Equip-Transit Mixer 01', 'Mixer', 'Retired', 1200.00)
            RETURNING equipment_id, equipment_name;
        """)
        equip_map = {name: eid for eid, name in cur.fetchall()}

        # -------------------------------------------------------------
        # 3. Create the 4 Enterprise Simulation Projects
        # -------------------------------------------------------------
        print("[3/6] Creating 4 enterprise projects across lifecycle stages...")
        
        # PRJ-101: Greenfield Eco-Villas (Planning, Barely Started, Eligible for Delete)
        cur.execute("""
            INSERT INTO projects (project_name, project_type, client_name, location, start_date, expected_end_date, budget, status)
            VALUES ('QA-SIM-101: Greenfield Eco-Villas', 'Residential', 'EcoLiving Ltd', 'Lonavala, MH', '2026-11-01', '2027-06-30', 12500000.00, 'Planning')
            RETURNING project_id;
        """)
        p101_id = cur.fetchone()[0]

        # PRJ-102: Metro Skyway Phase 2 (Active, Mid-Construction)
        cur.execute("""
            INSERT INTO projects (project_name, project_type, client_name, location, start_date, expected_end_date, budget, status)
            VALUES ('QA-SIM-102: Metro Skyway Phase 2', 'Infrastructure', 'Urban Transit Corp', 'Pune Metro Corridor', '2026-08-01', '2027-08-31', 45000000.00, 'Active')
            RETURNING project_id;
        """)
        p102_id = cur.fetchone()[0]

        # PRJ-103: Highland Medical Tower (Active, Near Completion)
        cur.execute("""
            INSERT INTO projects (project_name, project_type, client_name, location, start_date, expected_end_date, budget, status)
            VALUES ('QA-SIM-103: Highland Medical Tower', 'Commercial', 'Apex Healthcare Ltd', 'Baner, Pune', '2026-05-01', '2026-12-31', 32000000.00, 'Active')
            RETURNING project_id;
        """)
        p103_id = cur.fetchone()[0]

        # PRJ-104: Coastal Marina Hub (Completed, Full History, Must Be Protected)
        cur.execute("""
            INSERT INTO projects (project_name, project_type, client_name, location, start_date, expected_end_date, budget, status)
            VALUES ('QA-SIM-104: Coastal Marina Hub', 'Marine', 'Harbor Authority', 'Alibaug Port', '2025-06-01', '2026-04-30', 18000000.00, 'Completed')
            RETURNING project_id;
        """)
        p104_id = cur.fetchone()[0]

        print(f"Created Projects: P101={p101_id}, P102={p102_id}, P103={p103_id}, P104={p104_id}")

        # -------------------------------------------------------------
        # 4. Project Tasks Setup
        # -------------------------------------------------------------
        print("[4/6] Creating project tasks...")
        # P101: 1 planning task, 0% Not Started
        cur.execute("""
            INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage, description)
            VALUES (%s, %s, '2026-11-05', '2026-11-25', 'Not Started', 0.0, 'Initial topographical surveying')
            RETURNING project_task_id;
        """, (p101_id, tt_map['QA-Task-Site Survey']))
        pt_101_1 = cur.fetchone()[0]

        # P102: 4 tasks across lifecycle
        # Task 1: Piling (Completed 100%)
        cur.execute("""
            INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage, description)
            VALUES (%s, %s, '2026-08-05', '2026-09-15', 'Completed', 100.0, 'Bored cast-in-situ piling')
            RETURNING project_task_id;
        """, (p102_id, tt_map['QA-Task-Piling Work']))
        pt_102_1 = cur.fetchone()[0]

        # Task 2: Superstructure (In Progress 60%)
        cur.execute("""
            INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage, description)
            VALUES (%s, %s, '2026-09-16', '2026-11-30', 'In Progress', 60.0, 'Pier and pier cap casting')
            RETURNING project_task_id;
        """, (p102_id, tt_map['QA-Task-Superstructure']))
        pt_102_2 = cur.fetchone()[0]

        # Task 3: Finishing (Not Started 0%)
        cur.execute("""
            INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage, description)
            VALUES (%s, %s, '2026-12-01', '2027-04-30', 'Not Started', 0.0, 'Track bed and barrier works')
            RETURNING project_task_id;
        """, (p102_id, tt_map['QA-Task-Finishing']))
        pt_102_3 = cur.fetchone()[0]

        # P103: 2 tasks (1 Completed 100%, 1 In Progress 95%)
        cur.execute("""
            INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage, description)
            VALUES (%s, %s, '2026-05-10', '2026-08-31', 'Completed', 100.0, 'Substructure and tower frame')
            RETURNING project_task_id;
        """, (p103_id, tt_map['QA-Task-Superstructure']))
        pt_103_1 = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage, description)
            VALUES (%s, %s, '2026-09-01', '2026-12-20', 'In Progress', 95.0, 'Interior finishing and ward handover')
            RETURNING project_task_id;
        """, (p103_id, tt_map['QA-Task-Finishing']))
        pt_103_2 = cur.fetchone()[0]

        # P104: 2 tasks (both Completed 100%)
        cur.execute("""
            INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage, description)
            VALUES (%s, %s, '2025-06-15', '2025-11-30', 'Completed', 100.0, 'Marine piling and bulkhead')
            RETURNING project_task_id;
        """, (p104_id, tt_map['QA-Task-Piling Work']))
        pt_104_1 = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage, description)
            VALUES (%s, %s, '2025-12-01', '2026-04-15', 'Completed', 100.0, 'Dock deck and pavilion')
            RETURNING project_task_id;
        """, (p104_id, tt_map['QA-Task-Finishing']))
        pt_104_2 = cur.fetchone()[0]

        # -------------------------------------------------------------
        # 5. Purchases, Deliveries, Allocations & Consumption Setup
        # -------------------------------------------------------------
        print("[5/6] Creating procurement, delivery, and material usage transactions...")

        # PO 1: PRJ-102 (Delivered)
        cur.execute("""
            INSERT INTO purchases (supplier_id, project_id, purchase_date, status)
            VALUES (%s, %s, '2026-08-10', 'Delivered')
            RETURNING purchase_id;
        """, (sup_map['QA-Supplier-Alpha'], p102_id))
        po_102_1 = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO purchase_items (purchase_id, material_id, quantity, unit_price)
            VALUES 
            (%s, %s, 500.0, 380.00), -- 500 bags Cement @ 380 = 190,000
            (%s, %s, 20.0, 55000.00)  -- 20 tonnes Steel @ 55,000 = 1,100,000
        """, (po_102_1, mat_map['QA-Mat-Cement OPC 53'], po_102_1, mat_map['QA-Mat-TMT Steel Fe500']))

        # PO 2: PRJ-102 (Shipped - not yet delivered!)
        cur.execute("""
            INSERT INTO purchases (supplier_id, project_id, purchase_date, status)
            VALUES (%s, %s, '2026-10-20', 'Shipped')
            RETURNING purchase_id;
        """, (sup_map['QA-Supplier-Beta'], p102_id))
        po_102_2 = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO purchase_items (purchase_id, material_id, quantity, unit_price)
            VALUES (%s, %s, 40.0, 4500.00) -- 40 cu.m Concrete @ 4500 = 180,000
        """, (po_102_2, mat_map['QA-Mat-ReadyMix Concrete M30']))

        # PO 3: PRJ-102 (Ordered - pending procurement)
        cur.execute("""
            INSERT INTO purchases (supplier_id, project_id, purchase_date, status)
            VALUES (%s, %s, '2026-10-24', 'Ordered')
            RETURNING purchase_id;
        """, (sup_map['QA-Supplier-Alpha'], p102_id))
        po_102_3 = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO purchase_items (purchase_id, material_id, quantity, unit_price)
            VALUES (%s, %s, 100.0, 1800.00) -- 100 tonnes Sand @ 1800 = 180,000
        """, (po_102_3, mat_map['QA-Mat-River Sand']))

        # PO 4: PRJ-103 (Completed)
        cur.execute("""
            INSERT INTO purchases (supplier_id, project_id, purchase_date, status)
            VALUES (%s, %s, '2026-05-15', 'Completed')
            RETURNING purchase_id;
        """, (sup_map['QA-Supplier-Alpha'], p103_id))
        po_103_1 = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO purchase_items (purchase_id, material_id, quantity, unit_price)
            VALUES 
            (%s, %s, 800.0, 390.00), -- 800 bags Cement @ 390 = 312,000
            (%s, %s, 30.0, 56000.00)  -- 30 tonnes Steel @ 56,000 = 1,680,000
        """, (po_103_1, mat_map['QA-Mat-Cement OPC 53'], po_103_1, mat_map['QA-Mat-TMT Steel Fe500']))

        # PO 5: PRJ-104 (Completed)
        cur.execute("""
            INSERT INTO purchases (supplier_id, project_id, purchase_date, status)
            VALUES (%s, %s, '2025-07-01', 'Completed')
            RETURNING purchase_id;
        """, (sup_map['QA-Supplier-Beta'], p104_id))
        po_104_1 = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO purchase_items (purchase_id, material_id, quantity, unit_price)
            VALUES (%s, %s, 1200.0, 370.00) -- 1200 bags Cement @ 370 = 444,000
        """, (po_104_1, mat_map['QA-Mat-Cement OPC 53']))

        # Material Usage for PRJ-102 (Delivered 500 bags Cement, Allocated 350, Consumed 250)
        cur.execute("""
            INSERT INTO material_usage (project_id, material_id, quantity_allocated, quantity_used)
            VALUES 
            (%s, %s, 350.0, 250.0),
            (%s, %s, 15.0, 10.0)
        """, (p102_id, mat_map['QA-Mat-Cement OPC 53'], p102_id, mat_map['QA-Mat-TMT Steel Fe500']))

        # Material Usage for PRJ-103 (Delivered 800 bags Cement, Allocated 750, Consumed 700)
        cur.execute("""
            INSERT INTO material_usage (project_id, material_id, quantity_allocated, quantity_used)
            VALUES (%s, %s, 750.0, 700.0)
        """, (p103_id, mat_map['QA-Mat-Cement OPC 53']))

        # Material Usage for PRJ-104 (Delivered 1200 bags Cement, Allocated 1200, Consumed 1200)
        cur.execute("""
            INSERT INTO material_usage (project_id, material_id, quantity_allocated, quantity_used)
            VALUES (%s, %s, 1200.0, 1200.0)
        """, (p104_id, mat_map['QA-Mat-Cement OPC 53']))

        # -------------------------------------------------------------
        # 6. Workers, Equipment Assignments & Misc Expenses Setup
        # -------------------------------------------------------------
        print("[6/6] Creating worker assignments, equipment logs, and expenses...")

        # Worker assignments on PRJ-102 Task 1 & Task 2
        cur.execute("""
            INSERT INTO task_workers (project_task_id, worker_id, assigned_hours, locked_daily_rate)
            VALUES 
            (%s, %s, 160.0, 1800.00), -- Anil (Site Eng) on Task 1: 160 hrs = 20 days @ 1800 = 36,000
            (%s, %s, 120.0, 1200.00), -- Bikram (Foreman) on Task 2: 120 hrs = 15 days @ 1200 = 18,000
            (%s, %s, 80.0, 800.00)    -- Chetan (Mason) on Task 2: 80 hrs = 10 days @ 800 = 8,000
        """, (
            pt_102_1, worker_map['QA-Worker-Anil (Site Eng)'],
            pt_102_2, worker_map['QA-Worker-Bikram (Foreman)'],
            pt_102_2, worker_map['QA-Worker-Chetan (Mason)']
        ))

        # Worker assignments on PRJ-103 Task 1
        cur.execute("""
            INSERT INTO task_workers (project_task_id, worker_id, assigned_hours, locked_daily_rate)
            VALUES (%s, %s, 240.0, 1800.00) -- Anil on P103 Task 1: 240 hrs = 30 days @ 1800 = 54,000
        """, (pt_103_1, worker_map['QA-Worker-Anil (Site Eng)']))

        # Equipment assignments on PRJ-102
        cur.execute("""
            INSERT INTO equipment_assignments (equipment_id, project_task_id, start_date, end_date, hours_used, locked_hourly_rate)
            VALUES (%s, %s, '2026-08-10', '2026-09-10', 80.0, 2500.00) -- Tower Crane on Task 1: 80 hrs @ 2500 = 200,000
        """, (equip_map['QA-Equip-Tower Crane 01'], pt_102_1))

        # Equipment assignments on PRJ-103
        cur.execute("""
            INSERT INTO equipment_assignments (equipment_id, project_task_id, start_date, end_date, hours_used, locked_hourly_rate)
            VALUES (%s, %s, '2026-05-15', '2026-08-15', 120.0, 1500.00) -- Concrete Pump on P103: 120 hrs @ 1500 = 180,000
        """, (equip_map['QA-Equip-Concrete Pump 01'], pt_103_1))

        # Misc Expenses
        cur.execute("""
            INSERT INTO expenses (project_id, expense_date, expense_type, amount, description)
            VALUES 
            (%s, '2026-08-25', 'Site Security', 45000.00, 'Security personnel deployment month 1'),
            (%s, '2026-09-10', 'Statutory Permits', 80000.00, 'Municipal clearance fees'),
            (%s, '2026-06-01', 'Environmental Clearance', 120000.00, 'State pollution control board fee')
        """, (p102_id, p102_id, p103_id))

        conn.commit()
        print("\n" + "=" * 60)
        print("ENTERPRISE SIMULATION DATA SEEDED AND COMMITTED SUCCESSFULLY!")
        print("=" * 60)

    except Exception as e:
        conn.rollback()
        print(f"\nERROR seeding simulation: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    simulate_enterprise()
