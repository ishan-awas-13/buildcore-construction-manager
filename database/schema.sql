DROP VIEW IF EXISTS expense_ledger_view CASCADE;
DROP VIEW IF EXISTS equipment_status_view CASCADE;
DROP VIEW IF EXISTS worker_status_view CASCADE;
DROP VIEW IF EXISTS project_progress_view CASCADE;
DROP VIEW IF EXISTS purchases_with_total_view CASCADE;
DROP TABLE IF EXISTS expenses CASCADE;
DROP TABLE IF EXISTS purchase_items CASCADE;
DROP TABLE IF EXISTS purchases CASCADE;
DROP TABLE IF EXISTS material_usage CASCADE;
DROP TABLE IF EXISTS equipment_assignments CASCADE;
DROP TABLE IF EXISTS task_workers CASCADE;
DROP TABLE IF EXISTS project_tasks CASCADE;
DROP TABLE IF EXISTS task_types CASCADE;
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS project_workers CASCADE;
DROP TABLE IF EXISTS suppliers CASCADE;
DROP TABLE IF EXISTS equipment CASCADE;
DROP TABLE IF EXISTS materials CASCADE;
DROP TABLE IF EXISTS workers CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 0. Users (Authentication)
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL
);

-- 1. Projects
CREATE TABLE projects (
    project_id SERIAL PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    project_type VARCHAR(100) NOT NULL,
    client_name VARCHAR(255) NOT NULL,
    location TEXT NOT NULL,
    start_date DATE NOT NULL,
    expected_end_date DATE NOT NULL,
    budget NUMERIC(15, 2) NOT NULL CHECK (budget >= 0),
    status VARCHAR(50) NOT NULL DEFAULT 'Planning',
    CONSTRAINT check_end_date CHECK (expected_end_date >= start_date)
);

-- 2. Workers
CREATE TABLE workers (
    worker_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(100) NOT NULL,
    skill VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    daily_rate NUMERIC(10, 2) NOT NULL CHECK (daily_rate >= 0),
    status VARCHAR(50) NOT NULL DEFAULT 'Available'
);

-- 3. Materials
CREATE TABLE materials (
    material_id SERIAL PRIMARY KEY,
    material_name VARCHAR(255) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    unit_cost NUMERIC(10, 2) NOT NULL CHECK (unit_cost >= 0),
    minimum_stock NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (minimum_stock >= 0)
);

-- 4. Equipment
CREATE TABLE equipment (
    equipment_id SERIAL PRIMARY KEY,
    equipment_name VARCHAR(255) NOT NULL,
    equipment_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Available',
    hourly_rate NUMERIC(10, 2) NOT NULL CHECK (hourly_rate >= 0)
);

-- 5. Suppliers
CREATE TABLE suppliers (
    supplier_id SERIAL PRIMARY KEY,
    supplier_name VARCHAR(255) NOT NULL,
    contact_person VARCHAR(255),
    phone VARCHAR(20),
    email VARCHAR(255),
    address TEXT
);

-- 6. Project Workers (Many-to-Many)
CREATE TABLE project_workers (
    project_worker_id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    worker_id INT NOT NULL REFERENCES workers(worker_id) ON DELETE CASCADE,
    assigned_date DATE NOT NULL,
    release_date DATE,
    role_on_project VARCHAR(100) NOT NULL,
    CONSTRAINT check_release_date CHECK (release_date IS NULL OR release_date >= assigned_date)
);

-- 7. Task Types (Reusable construction activities)
CREATE TABLE task_types (
    task_type_id SERIAL PRIMARY KEY,
    task_name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT
);

-- 8. Project Tasks (Many-to-Many junction between Projects and Task Types)
CREATE TABLE project_tasks (
    project_task_id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    task_type_id INT NOT NULL REFERENCES task_types(task_type_id) ON DELETE RESTRICT,
    start_date DATE NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Not Started',
    completion_percentage NUMERIC(5, 2) NOT NULL DEFAULT 0 
        CHECK (completion_percentage >= 0 AND completion_percentage <= 100),
    description TEXT,
    CONSTRAINT uq_project_task UNIQUE (project_id, task_type_id),
    CONSTRAINT check_pt_due_date CHECK (due_date >= start_date)
);

-- 9. Task Workers (Workers assigned to project-specific tasks)
CREATE TABLE task_workers (
    task_worker_id SERIAL PRIMARY KEY,
    project_task_id INT NOT NULL REFERENCES project_tasks(project_task_id) ON DELETE CASCADE,
    worker_id INT NOT NULL REFERENCES workers(worker_id) ON DELETE CASCADE,
    assigned_hours NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (assigned_hours >= 0)
);

-- 10. Equipment Assignments (Many-to-Many over time)
CREATE TABLE equipment_assignments (
    assignment_id SERIAL PRIMARY KEY,
    equipment_id INT NOT NULL REFERENCES equipment(equipment_id) ON DELETE CASCADE,
    project_task_id INT NOT NULL REFERENCES project_tasks(project_task_id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date DATE,
    hours_used NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (hours_used >= 0),
    CONSTRAINT check_eq_end_date CHECK (end_date IS NULL OR end_date >= start_date)
);

-- 11. Material Usage (Many-to-Many)
CREATE TABLE material_usage (
    usage_id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    material_id INT NOT NULL REFERENCES materials(material_id) ON DELETE CASCADE,
    quantity_allocated NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (quantity_allocated >= 0),
    quantity_used NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (quantity_used >= 0)
);

-- 12. Purchases
CREATE TABLE purchases (
    purchase_id SERIAL PRIMARY KEY,
    supplier_id INT NOT NULL REFERENCES suppliers(supplier_id) ON DELETE RESTRICT,
    project_id INT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    purchase_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Pending'
);

-- 13. Purchase Items
CREATE TABLE purchase_items (
    purchase_item_id SERIAL PRIMARY KEY,
    purchase_id INT NOT NULL REFERENCES purchases(purchase_id) ON DELETE CASCADE,
    material_id INT NOT NULL REFERENCES materials(material_id) ON DELETE RESTRICT,
    quantity NUMERIC(10, 2) NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0)
);

-- 14. Expenses
CREATE TABLE expenses (
    expense_id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    expense_type VARCHAR(100) NOT NULL,
    amount NUMERIC(15, 2) NOT NULL CHECK (amount >= 0),
    expense_date DATE NOT NULL,
    description TEXT
);

-- VIEWS FOR DYNAMIC CALCULATIONS

-- View to calculate purchases with their total amount dynamically
CREATE VIEW purchases_with_total_view AS
SELECT 
    p.purchase_id,
    p.supplier_id,
    p.project_id,
    p.purchase_date,
    p.status,
    COALESCE(SUM(pi.quantity * pi.unit_price), 0) AS total_amount
FROM 
    purchases p
LEFT JOIN 
    purchase_items pi ON p.purchase_id = pi.purchase_id
GROUP BY 
    p.purchase_id;

-- View to calculate project progress based on average task completion (now using project_tasks)
CREATE VIEW project_progress_view AS
SELECT 
    p.project_id,
    p.project_name,
    COALESCE(AVG(pt.completion_percentage), 0) AS progress_percentage,
    COUNT(pt.project_task_id) AS total_tasks,
    SUM(CASE WHEN pt.status = 'Completed' THEN 1 ELSE 0 END) AS completed_tasks
FROM 
    projects p
LEFT JOIN 
    project_tasks pt ON p.project_id = pt.project_id
GROUP BY 
    p.project_id;

-- Dynamic Worker Status View
CREATE VIEW worker_status_view AS
SELECT w.*,
    CASE 
        WHEN w.status IN ('On Leave', 'Inactive') THEN w.status
        WHEN EXISTS (
            SELECT 1 FROM task_workers tw
            JOIN project_tasks pt ON tw.project_task_id = pt.project_task_id
            WHERE tw.worker_id = w.worker_id AND pt.status IN ('In Progress', 'Not Started')
        ) THEN 'Assigned'
        ELSE 'Available'
    END AS computed_status
FROM workers w;

-- Dynamic Equipment Status View
CREATE VIEW equipment_status_view AS
SELECT e.*,
    CASE 
        WHEN e.status IN ('Maintenance', 'Retired') THEN e.status
        WHEN EXISTS (
            SELECT 1 FROM equipment_assignments ea
            WHERE ea.equipment_id = e.equipment_id
            AND ea.start_date <= CURRENT_DATE 
            AND (ea.end_date IS NULL OR ea.end_date >= CURRENT_DATE)
        ) THEN 'In Use'
        ELSE 'Available'
    END AS computed_status
FROM equipment e;

-- Unified Financial Ledger View
-- Consolidates all 4 cost categories into a single queryable view.
-- Material cost = purchase_items (quantity * unit_price)
-- Labour cost = task_workers (assigned_hours / 8) * worker daily_rate
-- Equipment cost = equipment_assignments hours_used * equipment hourly_rate
-- Other cost = expenses table (misc/manual entries)
CREATE VIEW expense_ledger_view AS

-- MATERIALS: Cost comes from actual purchase line items
SELECT
    'MAT-' || pi.purchase_item_id AS transaction_id,
    p.project_id,
    p.purchase_date AS transaction_date,
    'Materials' AS category,
    m.material_name || ' — ' || pi.quantity || ' ' || m.unit || ' @ ₹' || pi.unit_price AS description,
    (pi.quantity * pi.unit_price) AS amount,
    'Purchase' AS source_type,
    p.purchase_id AS source_id
FROM purchase_items pi
JOIN purchases p ON pi.purchase_id = p.purchase_id
JOIN materials m ON pi.material_id = m.material_id

UNION ALL

-- LABOUR: Cost = (assigned_hours / 8) * daily_rate
SELECT
    'LAB-' || tw.task_worker_id AS transaction_id,
    pt.project_id,
    pt.start_date AS transaction_date,
    'Labour' AS category,
    w.name || ' — ' || tt.task_name || ' (' || tw.assigned_hours || ' hrs)' AS description,
    ROUND((tw.assigned_hours / 8.0) * w.daily_rate, 2) AS amount,
    'Labour' AS source_type,
    tw.task_worker_id AS source_id
FROM task_workers tw
JOIN workers w ON tw.worker_id = w.worker_id
JOIN project_tasks pt ON tw.project_task_id = pt.project_task_id
JOIN task_types tt ON pt.task_type_id = tt.task_type_id

UNION ALL

-- EQUIPMENT: Cost = hours_used * hourly_rate
SELECT
    'EQP-' || ea.assignment_id AS transaction_id,
    pt.project_id,
    ea.start_date AS transaction_date,
    'Equipment' AS category,
    eq.equipment_name || ' — ' || tt.task_name || ' (' || ea.hours_used || ' hrs)' AS description,
    ROUND(ea.hours_used * eq.hourly_rate, 2) AS amount,
    'Equipment' AS source_type,
    ea.assignment_id AS source_id
FROM equipment_assignments ea
JOIN equipment eq ON ea.equipment_id = eq.equipment_id
JOIN project_tasks pt ON ea.project_task_id = pt.project_task_id
JOIN task_types tt ON pt.task_type_id = tt.task_type_id

UNION ALL

-- OTHER / MISCELLANEOUS: Direct from expenses table
SELECT
    'MISC-' || e.expense_id AS transaction_id,
    e.project_id,
    e.expense_date AS transaction_date,
    'Other' AS category,
    e.expense_type || ' — ' || COALESCE(e.description, '') AS description,
    e.amount,
    'Misc Expense' AS source_type,
    e.expense_id AS source_id
FROM expenses e;
