# BuildCore SQL + Project Verification Guide for Presentation

This document contains the most important SQL commands and verification checks that demonstrate the project clearly during a presentation.

---

## 1. Start the project

Open PowerShell in the project folder and run:

```powershell
cd "c:\Users\ishan\OneDrive\Desktop\College_Files\SEM-5\Database Systems\BuildCore_DB_Project"
.\.venv\Scripts\Activate.ps1
flask run --debug
```

Then open:

```text
http://127.0.0.1:5000
```

Login:

```text
Use the demo administrator account configured for your local installation. Avoid sharing real credentials in a presentation copy.
```

---

## 2. Connect to PostgreSQL

Use the database name from the project configuration:

```powershell
psql -U postgres -h 127.0.0.1 -p 5432 -d buildcore
```

When prompted, enter the PostgreSQL password configured for your local installation. Do not include a real database password in a shared document.

Useful PostgreSQL commands:

```sql
\l
\dt
\d projects
\d project_tasks
\d material_usage
\d expenses
```

These commands show that the database and project tables exist.

---

## 3. Quick database verification queries

### 3.1 Show the main tables and row counts

```sql
SELECT
    (SELECT COUNT(*) FROM projects) AS total_projects,
    (SELECT COUNT(*) FROM workers) AS total_workers,
    (SELECT COUNT(*) FROM materials) AS total_materials,
    (SELECT COUNT(*) FROM equipment) AS total_equipment,
    (SELECT COUNT(*) FROM suppliers) AS total_suppliers,
    (SELECT COUNT(*) FROM project_tasks) AS total_tasks,
    (SELECT COUNT(*) FROM purchases) AS total_purchases,
    (SELECT COUNT(*) FROM expenses) AS total_expenses;
```

This is a strong presentation query because it immediately proves that the system has real data.

### 3.2 Show all projects

```sql
SELECT project_id, project_name, project_type, client_name, location, status, budget
FROM projects
ORDER BY project_id;
```

### 3.3 Show all workers

```sql
SELECT worker_id, name, role, skill, status, daily_rate
FROM workers
ORDER BY worker_id;
```

### 3.4 Show materials in stock / material catalog

```sql
SELECT material_id, material_name, unit, unit_cost
FROM materials
ORDER BY material_id;
```

### 3.5 Show suppliers

```sql
SELECT supplier_id, supplier_name, contact_person, phone, email
FROM suppliers
ORDER BY supplier_id;
```

---

## 4. Project management verification queries

### 4.1 Show assigned project tasks

```sql
SELECT p.project_name, tt.task_name, pt.status, pt.completion_percentage, pt.due_date
FROM project_tasks pt
JOIN projects p ON pt.project_id = p.project_id
JOIN task_types tt ON pt.task_type_id = tt.task_type_id
ORDER BY p.project_name, pt.due_date;
```

This demonstrates task planning and progress tracking.

### 4.2 Show task completion progress per project

```sql
SELECT project_name, progress_percentage, total_tasks, completed_tasks
FROM project_progress_view
ORDER BY progress_percentage DESC;
```

This is a very nice query for presentation because it shows the project progress view in action.

### 4.3 Show workers assigned to projects

```sql
SELECT p.project_name, w.name, pw.role_on_project, pw.assigned_date, pw.release_date
FROM project_workers pw
JOIN projects p ON pw.project_id = p.project_id
JOIN workers w ON pw.worker_id = w.worker_id
ORDER BY p.project_name, w.name;
```

### 4.4 Show workers assigned to specific tasks

```sql
SELECT p.project_name, tt.task_name, w.name, tw.assigned_hours
FROM task_workers tw
JOIN project_tasks pt ON tw.project_task_id = pt.project_task_id
JOIN projects p ON pt.project_id = p.project_id
JOIN task_types tt ON pt.task_type_id = tt.task_type_id
JOIN workers w ON tw.worker_id = w.worker_id
ORDER BY p.project_name, tt.task_name;
```

---

## 5. Material and equipment management verification

### 5.1 Show material usage across projects

```sql
SELECT p.project_name, m.material_name, mu.quantity_allocated, mu.quantity_used
FROM material_usage mu
JOIN projects p ON mu.project_id = p.project_id
JOIN materials m ON mu.material_id = m.material_id
ORDER BY p.project_name, m.material_name;
```

### 5.2 Show equipment assignments

```sql
SELECT p.project_name, e.equipment_name, e.equipment_type, ea.start_date, ea.end_date, ea.hours_used
FROM equipment_assignments ea
JOIN project_tasks pt ON ea.project_task_id = pt.project_task_id
JOIN projects p ON pt.project_id = p.project_id
JOIN equipment e ON ea.equipment_id = e.equipment_id
ORDER BY p.project_name, ea.start_date;
```

### 5.3 Show dynamic equipment status

```sql
SELECT equipment_name, equipment_type, computed_status, hourly_rate
FROM equipment_status_view
ORDER BY equipment_name;
```

### 5.4 Show dynamic worker status

```sql
SELECT name, role, skill, computed_status, daily_rate
FROM worker_status_view
ORDER BY name;
```

---

## 6. Financial verification queries

### 6.1 Show all purchases and status

```sql
SELECT p.purchase_id, s.supplier_name, pr.project_name, p.purchase_date, p.status
FROM purchases p
JOIN suppliers s ON p.supplier_id = s.supplier_id
JOIN projects pr ON p.project_id = pr.project_id
ORDER BY p.purchase_date DESC;
```

### 6.2 Show total purchase amount per order

```sql
SELECT p.purchase_id, s.supplier_name, pr.project_name, pv.total_amount, p.status
FROM purchases_with_total_view pv
JOIN purchases p ON pv.purchase_id = p.purchase_id
JOIN suppliers s ON p.supplier_id = s.supplier_id
JOIN projects pr ON p.project_id = pr.project_id
ORDER BY pv.total_amount DESC;
```

### 6.3 Show unified financial ledger

```sql
SELECT project_id, category, description, amount, transaction_date
FROM expense_ledger_view
ORDER BY transaction_date DESC;
```

### 6.4 Show total project spending

```sql
SELECT project_id,
       SUM(amount) AS total_spend
FROM expense_ledger_view
GROUP BY project_id
ORDER BY total_spend DESC;
```

---

## 7. Best presentation SQL queries to show the project

If you want only the strongest 5 queries for live demo, use these:

```sql
SELECT * FROM projects;
SELECT * FROM project_progress_view;
SELECT * FROM project_workers;
SELECT * FROM material_usage;
SELECT * FROM expense_ledger_view;
```

These queries clearly show that the project covers:

- project planning
- task tracking
- workforce allocation
- material control
- financial tracking

---

## 8. What to say while presenting

You can explain:

> “This system is designed for construction project management. The database stores project information, team assignments, task progress, materials, equipment, suppliers, and financial transactions. The application uses relational tables to link projects with tasks, workers, purchases, and expenses. The SQL queries prove that data is being recorded and monitored in real time.”

---

## 9. Verification checklist

Before presenting, confirm all of these:

- [ ] PostgreSQL is running
- [ ] Database buildcore exists
- [ ] Tables are created
- [ ] Projects have data
- [ ] Workers and tasks are assigned
- [ ] Material usage is stored
- [ ] Purchase and expense records exist
- [ ] Flask app is running successfully
- [ ] Login works with the locally configured demo administrator account

---

## 10. Final demo summary

A strong final demonstration flow is:

1. Start Flask app
2. Open the app in browser
3. Login as admin
4. Show project dashboard
5. Run SQL queries in psql
6. Show project data, task progress, materials, and financial ledger
7. Explain how the relational database supports the application

This combination of web app + SQL verification makes the project presentation clear and convincing.
