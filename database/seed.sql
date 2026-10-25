-- Clear existing business data (preserve users table for auth continuity)
TRUNCATE projects, workers, materials, equipment, suppliers, project_workers, task_types, project_tasks, task_workers, equipment_assignments, material_usage, purchases, purchase_items, expenses RESTART IDENTITY CASCADE;

-- Users are intentionally NOT seeded here.
-- Run `flask create-admin` to configure a secure admin account interactively.

-- ============================================================
-- PROJECTS: Indian Construction Context (Current Anchor: 26 October 2026)
-- Chronologically aligned: Historical completed, current active, and planning
-- ============================================================
INSERT INTO projects (project_name, project_type, client_name, location, start_date, expected_end_date, budget, status) VALUES
('Navi Mumbai International Airport T2', 'Infrastructure', 'CIDCO', 'Navi Mumbai, Maharashtra', '2025-06-01', '2027-12-31', 500000000.00, 'Active'),
('Delhi-Mumbai Expressway Phase 4', 'Roadways', 'NHAI', 'Vadodara, Gujarat', '2024-05-10', '2026-08-31', 850000000.00, 'Completed'),
('Cyber City IT Park', 'Commercial', 'DLF', 'Gurugram, Haryana', '2025-08-01', '2027-08-31', 300000000.00, 'Active'),
('Ganga River Bridge', 'Infrastructure', 'Govt of Bihar', 'Patna, Bihar', '2024-02-15', '2027-06-30', 450000000.00, 'Delayed'),
('Prestige Sunrise Apartments', 'Residential', 'Prestige Group', 'Bengaluru, Karnataka', '2025-04-01', '2027-06-30', 250000000.00, 'Active'),
('Kochi Metro Extension', 'Infrastructure', 'KMRL', 'Kochi, Kerala', '2026-01-01', '2028-12-31', 600000000.00, 'Active'),
('Tata Steel Plant Expansion', 'Industrial', 'Tata Steel', 'Jamshedpur, Jharkhand', '2024-01-15', '2026-06-30', 750000000.00, 'Completed'),
('Heritage Museum Renovation', 'Commercial', 'ASI', 'Jaipur, Rajasthan', '2023-01-10', '2024-12-15', 50000000.00, 'Completed');

-- ============================================================
-- WORKERS: Skilled personnel register
-- ============================================================
INSERT INTO workers (name, role, skill, phone, daily_rate, status) VALUES
('Ramesh Kumar', 'Mason', 'Bricklaying', '9876543210', 800.00, 'Available'),
('Suresh Singh', 'Electrician', 'Wiring', '9876543211', 1000.00, 'Assigned'),
('Amit Patel', 'Plumber', 'Pipe Fitting', '9876543212', 900.00, 'Assigned'),
('Vikram Sharma', 'Site Engineer', 'Supervision', '9876543213', 2500.00, 'Assigned'),
('Rajesh Verma', 'Carpenter', 'Woodwork', '9876543214', 950.00, 'Available'),
('Manoj Das', 'Welder', 'Metalwork', '9876543215', 1100.00, 'Assigned'),
('Anil Gupta', 'Painter', 'Finishing', '9876543216', 750.00, 'Available'),
('Sunil Yadav', 'Laborer', 'General', '9876543217', 500.00, 'Assigned'),
('Prakash Tiwari', 'Crane Operator', 'Heavy Machinery', '9876543218', 1500.00, 'Available'),
('Karan Singh', 'Surveyor', 'Land Surveying', '9876543219', 2000.00, 'Available'),
('Rahul Mehra', 'Mason', 'Plastering', '9876543220', 850.00, 'Available'),
('Deepak Joshi', 'Electrician', 'High Voltage', '9876543221', 1200.00, 'Assigned'),
('Vijay Kumar', 'Plumber', 'Sanitary', '9876543222', 900.00, 'Available'),
('Sanjay Mishra', 'Project Manager', 'Management', '9876543223', 4000.00, 'Assigned'),
('Arvind Patel', 'Carpenter', 'Formwork', '9876543224', 1000.00, 'Available'),
('Nitin Desai', 'Welder', 'Structural', '9876543225', 1150.00, 'Available'),
('Ajay Sharma', 'Painter', 'Exterior', '9876543226', 800.00, 'Available'),
('Pramod Kumar', 'Laborer', 'General', '9876543227', 500.00, 'Assigned'),
('Ganesh Iyer', 'Excavator Operator', 'Heavy Machinery', '9876543228', 1400.00, 'Available'),
('Ravi Varma', 'Safety Officer', 'Safety', '9876543229', 2200.00, 'Available');

-- ============================================================
-- MATERIALS: Master construction materials
-- ============================================================
INSERT INTO materials (material_name, unit, unit_cost) VALUES
('Portland Cement (50kg)', 'Bag', 400.00),
('TMT Steel Bars (12mm)', 'Tonne', 65000.00),
('River Sand', 'Cubic Meter', 1200.00),
('Crushed Stone Aggregate', 'Cubic Meter', 1500.00),
('Red Bricks', '1000 Pieces', 6000.00),
('Ready Mix Concrete (M30)', 'Cubic Meter', 4500.00),
('Copper Wire (2.5 sq mm)', 'Coil (90m)', 1800.00),
('PVC Pipes (4 inch)', 'Piece (6m)', 800.00),
('Ceramic Tiles (2x2 ft)', 'Box', 600.00),
('Emulsion Paint (20L)', 'Bucket', 3500.00),
('Aluminium Windows', 'Square Foot', 350.00),
('Teak Wood', 'Cubic Foot', 4000.00),
('Gypsum Board', 'Piece', 500.00),
('Waterproofing Chemical', 'Liter', 250.00),
('Scaffolding Pipes', 'Piece', 650.00);

-- ============================================================
-- EQUIPMENT: Machinery and vehicle assets
-- ============================================================
INSERT INTO equipment (equipment_name, equipment_type, status, hourly_rate) VALUES
('CAT 320 Excavator', 'Excavator', 'Available', 1500.00),
('JCB 3DX Backhoe Loader', 'Backhoe', 'Available', 800.00),
('Potain Tower Crane', 'Crane', 'In Use', 2500.00),
('Ajax Fiori Concrete Mixer', 'Mixer', 'Available', 1200.00),
('Volvo Compactor', 'Roller', 'Available', 1000.00),
('Mahindra Blazo Dump Truck', 'Truck', 'Available', 900.00),
('Schwing Stetter Concrete Pump', 'Pump', 'Maintenance', 2000.00),
('Atlas Copco Compressor', 'Compressor', 'Available', 400.00),
('Honda Portable Generator', 'Generator', 'Available', 300.00),
('Escorts Hydra Crane', 'Mobile Crane', 'Available', 1100.00);

-- ============================================================
-- SUPPLIERS
-- ============================================================
INSERT INTO suppliers (supplier_name, contact_person, phone, email, address) VALUES
('UltraTech Cement Ltd', 'Rajiv Singh', '9811111111', 'sales@ultratech.com', 'Andheri, Mumbai'),
('Tata Tiscon', 'Amitava Das', '9822222222', 'orders@tatatiscon.com', 'Salt Lake, Kolkata'),
('Godrej Construction', 'Priya Sharma', '9833333333', 'contact@godrejconst.com', 'Vikhroli, Mumbai'),
('Kajaria Ceramics', 'Sandeep Jain', '9844444444', 'b2b@kajaria.com', 'Nehru Place, New Delhi'),
('Asian Paints', 'Vikram Rathore', '9855555555', 'projects@asianpaints.com', 'Santacruz, Mumbai'),
('Finolex Pipes', 'Rahul Deshmukh', '9866666666', 'sales@finolex.com', 'Pimpri, Pune'),
('L&T Equipment Dealers', 'Narayanan K', '9877777777', 'equip@lntecc.com', 'Guindy, Chennai'),
('Shreeji Sand & Aggregates', 'Mukesh Patel', '9888888888', 'shreeji.sand@gmail.com', 'Navrangpura, Ahmedabad');

-- ============================================================
-- PROJECT WORKERS: Legacy project-level supervisor assignments
-- ============================================================
INSERT INTO project_workers (project_id, worker_id, assigned_date, role_on_project) VALUES
(1, 4, '2025-06-01', 'Lead Site Engineer'),
(1, 14, '2025-06-01', 'Project Manager'),
(1, 6, '2026-04-01', 'Structural Welder'),
(2, 19, '2024-05-15', 'Excavator Operator'),
(2, 10, '2024-05-10', 'Chief Surveyor'),
(3, 12, '2026-10-01', 'Electrical Lead'),
(3, 1, '2025-08-10', 'Head Mason'),
(4, 6, '2024-03-01', 'Structural Welder'),
(4, 16, '2024-03-15', 'Welding Inspector'),
(5, 2, '2026-06-01', 'Electrical Supervisor'),
(7, 20, '2024-01-15', 'Chief Safety Officer');

-- ============================================================
-- TASK TYPES: Standardized reusable construction activities
-- ============================================================
INSERT INTO task_types (task_name, description) VALUES
('Site Clearance', 'Clearing and preparing the construction site, removing debris and vegetation'),
('Foundation', 'Laying the structural foundation including piling, footings, and base slabs'),
('Brickwork', 'Exterior and interior wall construction using bricks and mortar'),
('Electrical Installation', 'Complete electrical wiring, panel installation, and fixture setup'),
('Plumbing', 'Water supply lines, drainage systems, and sanitary fittings installation'),
('Painting', 'Interior and exterior painting, finishing, and coating application'),
('Structural Steelwork', 'Erecting steel beams, columns, and structural framework'),
('Land Leveling', 'Grading and leveling terrain for construction or road laying'),
('Asphalt Surfacing', 'Laying asphalt layers for road or pavement construction'),
('Roofing', 'Roof structure installation, waterproofing, and insulation');

-- ============================================================
-- PROJECT TASKS: Aligned with current anchor date (26 October 2026)
-- Due date < 2026-10-26: Completed (100%)
-- Due date >= 2026-10-26: In Progress (10-80%) or Not Started (0%)
-- ============================================================

-- Project 1: Navi Mumbai International Airport T2 (Active)
INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage, description) VALUES
(1, 1, '2025-06-01', '2025-08-31', 'Completed', 100, 'Clear the airport terminal area'),
(1, 2, '2025-09-01', '2026-03-31', 'Completed', 100, 'Drive piles for terminal foundation'),
(1, 4, '2026-11-01', '2027-06-30', 'Not Started', 0, 'Terminal building electrical systems'),
(1, 7, '2026-04-01', '2026-12-31', 'In Progress', 65, 'Main terminal structural steel framework');

-- Project 2: Delhi-Mumbai Expressway Phase 4 (Completed)
INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage, description) VALUES
(2, 1, '2024-05-10', '2024-08-31', 'Completed', 100, 'Clear the 50km expressway corridor'),
(2, 8, '2024-09-01', '2025-03-31', 'Completed', 100, 'Level the 50km stretch'),
(2, 9, '2025-04-01', '2026-08-31', 'Completed', 100, 'Final road surface asphalt laying');

-- Project 3: Cyber City IT Park (Active)
INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage, description) VALUES
(3, 1, '2025-08-01', '2025-10-31', 'Completed', 100, 'Clear IT park construction site'),
(3, 2, '2025-11-01', '2026-04-30', 'Completed', 100, 'Deep foundation for 20-storey towers'),
(3, 3, '2026-05-01', '2026-09-30', 'Completed', 100, 'Multi-storey brickwork for office blocks'),
(3, 4, '2026-10-01', '2027-04-30', 'In Progress', 20, 'IT Park electrical and networking infrastructure'),
(3, 7, '2026-07-01', '2026-11-30', 'In Progress', 75, 'Erecting steel and concrete columns');

-- Project 4: Ganga River Bridge (Delayed)
INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage, description) VALUES
(4, 1, '2024-02-15', '2024-05-31', 'Completed', 100, 'Clear the river bank construction zone'),
(4, 2, '2024-06-01', '2025-09-30', 'Completed', 100, 'Deep water foundation and caissons'),
(4, 7, '2025-10-01', '2027-03-31', 'In Progress', 45, 'Bridge deck structural steelwork');

-- Project 5: Prestige Sunrise Apartments (Active)
INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage, description) VALUES
(5, 2, '2025-04-01', '2025-10-31', 'Completed', 100, 'Residential tower foundation'),
(5, 3, '2025-11-01', '2026-05-31', 'Completed', 100, 'Apartment exterior and interior brickwork'),
(5, 4, '2026-06-01', '2026-11-30', 'In Progress', 65, 'Apartment unit electrical concealing and wiring'),
(5, 5, '2026-08-01', '2026-12-31', 'In Progress', 40, 'Water supply and drainage for all floors'),
(5, 6, '2027-01-01', '2027-05-31', 'Not Started', 0, 'Interior and exterior painting'),
(5, 10, '2026-09-15', '2027-01-31', 'In Progress', 25, 'Terrace roofing and waterproofing');

-- Project 7: Tata Steel Plant Expansion (Completed)
INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage, description) VALUES
(7, 1, '2024-01-15', '2024-04-30', 'Completed', 100, 'Clear the plant expansion area'),
(7, 2, '2024-05-01', '2024-11-30', 'Completed', 100, 'Heavy industrial foundation for furnace'),
(7, 7, '2024-12-01', '2025-09-30', 'Completed', 100, 'Industrial grade structural steelwork'),
(7, 4, '2025-10-01', '2026-06-30', 'Completed', 100, 'High voltage electrical installation');

-- Project 8: Heritage Museum Renovation (Completed)
INSERT INTO project_tasks (project_id, task_type_id, start_date, due_date, status, completion_percentage, description) VALUES
(8, 3, '2023-01-10', '2023-09-30', 'Completed', 100, 'Heritage-safe brick restoration'),
(8, 6, '2023-10-01', '2024-05-31', 'Completed', 100, 'Heritage-safe paint application'),
(8, 4, '2023-06-01', '2024-02-28', 'Completed', 100, 'Museum electrical rewiring and lighting'),
(8, 5, '2023-08-01', '2024-04-30', 'Completed', 100, 'Updated plumbing for public facilities');

-- ============================================================
-- TASK WORKERS: Labor assignments to project tasks
-- ============================================================
INSERT INTO task_workers (project_task_id, worker_id, assigned_hours) VALUES
-- Airport T2: Site Clearance (pt_id=1, completed)
(1, 19, 160),
-- Airport T2: Foundation (pt_id=2, completed)
(2, 9, 320),
-- Airport T2: Structural Steelwork (pt_id=4, active)
(4, 6, 280),
-- Expressway: Land Leveling (pt_id=6, completed)
(6, 10, 240),
-- IT Park: Brickwork (pt_id=10, completed)
(10, 1, 300),
-- IT Park: Electrical (pt_id=11, active)
(11, 12, 180),
-- Apartments: Brickwork (pt_id=17, completed)
(17, 1, 500),
(17, 11, 400),
-- Apartments: Electrical (pt_id=18, active)
(18, 2, 250),
-- Apartments: Plumbing (pt_id=19, active)
(19, 3, 200),
-- Heritage Museum: Painting (pt_id=27, completed)
(27, 17, 450),
(27, 7, 300);

-- ============================================================
-- EQUIPMENT ASSIGNMENTS: Machinery deployment with accurate date boundaries
-- ============================================================
INSERT INTO equipment_assignments (equipment_id, project_task_id, start_date, end_date, hours_used) VALUES
(3, 2, '2025-09-15', '2026-03-31', 450), -- Potain Tower Crane -> Airport Foundation (Completed)
(1, 6, '2024-09-15', '2025-03-31', 1200), -- CAT 320 Excavator -> Expressway Land Leveling (Completed)
(6, 7, '2025-05-01', '2026-08-31', 800),  -- Mahindra Dump Truck -> Expressway Asphalt (Completed)
(4, 9, '2025-11-20', '2026-04-30', 300),  -- Ajax Fiori Mixer -> IT Park Foundation (Completed)
(9, 17, '2025-12-15', '2026-05-31', 600), -- Honda Generator -> Apartments Brickwork (Completed)
(10, 22, '2024-02-01', '2024-04-30', 950),-- Escorts Crane -> Tata Steel Clearance (Completed)
(3, 4, '2026-05-01', '2026-12-31', 350);  -- Potain Tower Crane -> Airport Steelwork (Currently In Use)

-- ============================================================
-- MATERIAL USAGE
-- ============================================================
INSERT INTO material_usage (project_id, material_id, quantity_allocated, quantity_used) VALUES
(1, 6, 5000, 2000),
(1, 2, 1000, 450),
(2, 4, 15000, 15000),
(3, 1, 10000, 8000),
(3, 2, 500, 250),
(5, 5, 500, 500),
(5, 1, 2000, 1800),
(5, 7, 100, 60);

-- ============================================================
-- PURCHASES
-- ============================================================
INSERT INTO purchases (supplier_id, project_id, purchase_date, status) VALUES
(1, 3, '2025-09-15', 'Delivered'),
(2, 1, '2025-06-20', 'Delivered'),
(8, 2, '2024-06-05', 'Delivered'),
(5, 8, '2023-08-20', 'Delivered'),
(4, 5, '2026-03-01', 'Delivered'),
(6, 5, '2025-11-10', 'Delivered'),
(2, 7, '2024-02-20', 'Delivered');

-- ============================================================
-- PURCHASE ITEMS
-- ============================================================
INSERT INTO purchase_items (purchase_id, material_id, quantity, unit_price) VALUES
(1, 1, 10000, 390.00),
(2, 2, 1000, 64000.00),
(3, 4, 15000, 1450.00),
(4, 10, 50, 3400.00),
(5, 9, 500, 580.00),
(6, 8, 200, 750.00),
(7, 2, 2000, 63000.00);

-- ============================================================
-- EXPENSES: Chronologically aligned
-- ============================================================
INSERT INTO expenses (project_id, expense_type, amount, expense_date, description) VALUES
(1, 'Labour', 450000.00, '2026-08-31', 'August Labour Wages'),
(1, 'Equipment', 250000.00, '2026-08-31', 'Tower Crane rental and maintenance'),
(2, 'Transportation', 150000.00, '2025-12-31', 'Aggregate transport costs'),
(3, 'Miscellaneous', 50000.00, '2025-08-15', 'Site office setup and permits'),
(5, 'Labour', 300000.00, '2026-07-31', 'July Labour Wages'),
(8, 'Labour', 120000.00, '2024-05-30', 'Painters and restorers wages');
