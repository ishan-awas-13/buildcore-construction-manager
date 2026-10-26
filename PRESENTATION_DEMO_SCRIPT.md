# BuildCore Presentation Demo Script & Teacher Evaluation Guide

This document is your step-by-step presentation script for demonstrating BuildCore to your database systems professor/evaluator. It is organized into **6 High-Impact Live Demos**, followed by **Database SQL Queries** and **Professor Viva Questions & Answers**.

---

## 🎯 Pre-Demo Checklist (Before Calling the Teacher)

1. Ensure PostgreSQL is running.
2. Ensure Flask is running in terminal:
   ```powershell
   flask run --debug
   ```
3. Open your browser at:
   ```text
   http://127.0.0.1:5000/
   ```
4. Have a secondary PowerShell terminal ready connected to PostgreSQL:
   ```powershell
   psql -U postgres -h 127.0.0.1 -p 5432 -d buildcore_copy
   ```

---

## 🎬 The 6 Live Demonstration Steps

---

### DEMO 1: Executive Dashboard & Live Database Introspection
**Concept**: Real-time aggregation via SQL, dynamic database introspection, and modern UI design.

1. **In the Browser**:
   - Go to `http://127.0.0.1:5000/dashboard`.
   - **Show the Bottom-Left Sidebar**: Point to the subtle transparency text showing the live active PostgreSQL database (`Connected DB: buildcore_copy`).
   - **Show the Metric Cards**: Point out the active KPI cards (Total Projects, Budget Committed, Total Workforce, Machinery Units). Mention that these are live SQL aggregates.
   - **Show the Active Projects Table**: Show the rounded soft table styling with royal blue headers, and point to the progress meters displaying **crisp bold black font numbers** (e.g. `100%`, `75%`, `20%`).
2. **What to tell your teacher**:
   > *"Professor, our application features dynamic database introspection where the active database catalog is inspected live. The dashboard provides real-time executive summaries computed directly from our underlying relational schema rather than hardcoded counter tables."*

---

### DEMO 2: Project-First Architecture & Workspace Navigation
**Concept**: Contextual normalization, work breakdown structure (WBS), and eliminating spreadsheet fragmentation.

1. **In the Browser**:
   - In the Active Projects table, click **"Workspace"** for **Project 1** (*Navi Mumbai International Airport T2*).
   - Point out the **7 dedicated workspace tabs**:
     - `Overview`: High-level timeline, budget utilization meter, and recent tasks.
     - `Tasks`: Work breakdown structure with completion meters and assigned resource badges.
     - `Workers`: Task-level staffing assignments with labor cost calculations.
     - `Equipment`: Heavy machinery allocations with operational hours.
     - `Materials`: Project-isolated inventory (allocated vs. consumed).
     - `Purchases`: Vendor procurement pipeline linked to this project.
     - `Financials`: 4-category cost ledger breakdown and budget utilization.
2. **What to tell your teacher**:
   > *"In civil engineering, resources do not float loosely—they belong to projects and specific tasks. We built a Project-First relational architecture where all labor, machinery, procurement, and cost accounting are contextualized per project."*

---

### DEMO 3: Resource Scheduling Intelligence & Real-Time Collision Prevention
**Concept**: Many-to-Many junction tables with temporal attributes, automated dynamic views (`worker_status_view`, `equipment_status_view`), and date-range overlap collision algorithms.

1. **In the Browser**:
   - In Project 1 Workspace, click the **"Workers"** tab.
   - Click the green button: **"+ Assign Worker to Task"**.
   - A modal opens.
   - **Select Task**: Choose `Interior Fitout & Finishes` (or any active task).
   - **Trigger Collision**: In the worker dropdown, select **Ramesh Kumar** (or **Suresh Singh**).
   - **Watch the Instant Alert**: A red warning box immediately appears inside the modal:
     > ⚠️ **"Schedule Collision Detected!"**  
     > Shows the exact overlapping project name, task name, and dates.
   - Note that the dropdown is highlighted red (`is-invalid`) and the **Submit button is automatically disabled**!
   - **Trigger Clear State**: Now select a worker who is available (e.g., `Amit Sharma`).
   - A green notification box appears:
     > ✅ **"Schedule Clear! Ready for immediate deployment."**
   - The Submit button re-enables!
2. **What to tell your teacher**:
   > *"Professor, spreadsheet tracking frequently causes resource double-booking. We solved this with scheduling intelligence: our UI performs date-range overlap validation (`start_a <= end_b AND end_a >= start_b`), while our PostgreSQL view `worker_status_view` dynamically computes resource availability on the fly. It is mathematically impossible for a worker or machine to get double-booked or have a stale status."*

---

### DEMO 4: Task Progress & Status Two-Way Synchronization with Database CHECK Constraints
**Concept**: Database-level domain integrity, PostgreSQL `CHECK` constraints, and duration-weighted progress aggregation (`project_progress_view`).

1. **In the Browser**:
   - In Project 1 Workspace, click the **"Tasks"** tab.
   - Find a task with `< 100%` progress. Click **"Edit"**.
   - Change the completion percentage to `100` and submit.
   - **Result**: The system automatically transitions the status to **"Completed"** and updates the progress bar to green `100%`.
   - Now click the **"Overview"** tab: point out that the overall project progress percentage has recalculated dynamically using duration-weighted mathematics via `project_progress_view`.
2. **In the PostgreSQL Terminal (Show DB Enforcement)**:
   - Run this query to show your teacher what happens if an invalid update bypasses the UI:
     ```sql
     UPDATE project_tasks SET completion_percentage = 75.00 WHERE project_task_id = 4;
     ```
     *(Assuming task 4 is 'Completed')*
   - **PostgreSQL Output**:
     ```text
     ERROR: new row for relation "project_tasks" violates check constraint "check_task_completion_status"
     ```
3. **What to tell your teacher**:
   > *"We do not rely solely on frontend JavaScript validation. We enforce data integrity directly in the PostgreSQL kernel using check constraints. A task cannot be marked 'Completed' unless its progress is exactly 100%, and a 'Not Started' task cannot have progress greater than 0%. Even a rogue SQL query is stopped by the database engine."*

---

### DEMO 5: Master-Detail Procurement & Project Material Isolation
**Concept**: 1:N Master-Detail relationship (`purchases` & `purchase_items`), isolated project material inventory (`material_usage`), and accrual accounting recognition.

1. **In the Browser**:
   - In Project 1 Workspace, click the **"Purchases"** tab.
   - Click **"+ New Purchase Order"**. Notice the project is pre-selected and locked.
   - Select a Supplier (e.g. `UltraTech Cement Ltd.`), choose Material `Portland Cement (50kg)`, quantity `50`, and submit.
   - Notice the initial purchase status is **"Pending"** or **"Ordered"**.
   - Check the **"Financials"** tab: the ₹ cost is **not yet added** to expenses because it has not been delivered.
   - Return to **"Purchases"**, click **"View"**, and update status to **"Delivered"**.
   - Now go to the **"Materials"** tab: notice the project stock has increased by 50 units!
   - Now go to the **"Financials"** tab: the material purchase is now recognized in the ledger!
2. **What to tell your teacher**:
   > *"We model a real procurement pipeline using a master-detail structure. Crucially, we enforce project material isolation: materials purchased for Project A cannot leak into Project B. Furthermore, expenses are recognized on delivery, adhering to standard accrual accounting principles."*

---

### DEMO 6: Financial Integrity, Snapshot Pricing & History Protection Guard
**Concept**: Snapshot pricing (historical rate freezing), financial ledgers via `UNION ALL` view (`expense_ledger_view`), and foreign key cascade protection.

1. **In the Browser**:
   - Go to the **"Financials"** tab of Project 1.
   - Show the 4-category breakdown:
     - 🧱 **Materials**: Actual delivered purchase line items.
     - 👷 **Labour**: Hours assigned &times; `locked_daily_rate`.
     - 🚜 **Equipment**: Hours used &times; `locked_hourly_rate`.
     - 📋 **Other Expenses**: Permits, surveys, testing.
2. **Explain Snapshot Pricing**:
   - Show that `task_workers` has `locked_daily_rate` and `equipment_assignments` has `locked_hourly_rate`.
   - Explain: *"If a crane rental company raises its rate from ₹2,000/hr to ₹3,500/hr next month, past project costs must NOT change. By snapshotting the rate at assignment time, our historical financials remain 100% immutable and audit-compliant."*
3. **Show the History Protection Guard**:
   - In the navigation, go to **Projects List** (`http://127.0.0.1:5000/projects/`).
   - Try to delete an active project with financial records (Project 1).
   - The deletion is blocked by the backend History Guard with an alert:
     > 🛡️ *"Cannot delete project with active purchase orders and historical financial records. Audit integrity protected."*
4. **What to tell your teacher**:
   > *"In production databases, unchecked cascading deletes can destroy millions of rupees of historical audit logs. We implemented a History Protection Guard that blocks deletions of projects with active financial commitments."*

---

## 💻 SQL Queries to Run Live in `psql` (If Requested)

If your professor says: *"Show me the database queries or schema in PostgreSQL"*, run these:

### 1. Show Table Row Counts & Database Scale
```sql
SELECT
    (SELECT COUNT(*) FROM projects) AS projects,
    (SELECT COUNT(*) FROM workers) AS workers,
    (SELECT COUNT(*) FROM equipment) AS equipment,
    (SELECT COUNT(*) FROM materials) AS materials,
    (SELECT COUNT(*) FROM project_tasks) AS tasks,
    (SELECT COUNT(*) FROM purchases) AS purchases,
    (SELECT COUNT(*) FROM material_usage) AS material_stocks;
```

### 2. Demonstrate Dynamic Worker Availability View
```sql
SELECT worker_id, name, role, status, computed_status 
FROM worker_status_view 
ORDER BY worker_id LIMIT 6;
```
*(Explain how `computed_status` calculates whether the worker is currently assigned to an ongoing task).*

### 3. Demonstrate Duration-Weighted Project Progress View
```sql
SELECT project_id, project_name, ROUND(progress_percentage, 1) AS progress_pct, total_tasks, completed_tasks 
FROM project_progress_view 
ORDER BY project_id;
```

### 4. Demonstrate the Unified 4-Category Expense Ledger View
```sql
SELECT category, COUNT(*) AS transactions, SUM(amount) AS total_spent 
FROM expense_ledger_view 
WHERE project_id = 1 
GROUP BY category;
```

### 5. Inspect Check Constraints on `project_tasks`
```sql
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'project_tasks'::regclass;
```

---

## 🎓 Professor Viva Questions & Model Answers

### Q1: Why did you use `task_workers` instead of directly linking workers to projects?
> **Answer**: *"Linking workers directly to projects (`project_workers`) only gives coarse macro-level assignment. In construction, workers are deployed to specific tasks (e.g. electrical, excavation) with distinct date windows and daily hours. By assigning workers to `project_tasks` via `task_workers`, we achieve precise task-level costing, scheduling conflict detection, and duration tracking."*

### Q2: Why use SQL Views instead of storing 'status' directly in the worker/equipment table?
> **Answer**: *"Storing computed status as a static column creates data anomaly risks. If a task ends or dates change, a static column requires manual updates and inevitably gets 'stuck' or desynchronized. With dynamic views like `worker_status_view`, the database derives availability in real-time from active task date ranges. It eliminates redundant state storage and guarantees 100% consistency."*

### Q3: What is 'Snapshot Pricing' and why is it needed in your schema?
> **Answer**: *"In `task_workers` and `equipment_assignments`, we record `locked_daily_rate` and `locked_hourly_rate`. If the master rate in `workers` or `equipment` increases next year due to inflation, historical financial ledgers must not change retroactively. Snapshot pricing freezes the unit rate at the moment of allocation, preserving accounting audit compliance."*

### Q4: How is your database normalized?
> **Answer**: *"Our schema satisfies Third Normal Form (3NF) and BCNF. All non-key attributes are fully functionally dependent on the primary key, with zero transitive dependencies. Reusable templates (`task_types`, `materials`, `suppliers`) are decoupled from instance tables (`project_tasks`, `material_usage`, `purchase_items`). Many-to-many relationships are resolved via dedicated junction tables with composite business attributes."*

### Q5: How do you handle cascade deletes safely?
> **Answer**: *"We use `ON DELETE CASCADE` for tightly coupled child records (like deleting a project removing its tasks and internal allocations). However, for master catalogs (`suppliers`, `task_types`, `materials`), we enforce `ON DELETE RESTRICT` to prevent accidental deletion of referenced master entities. In addition, our backend implements a History Protection Guard to prevent deleting active projects with audited financial trails."*
