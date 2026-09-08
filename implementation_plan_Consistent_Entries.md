# Dynamic Status Engine — Implementation Plan

You've highlighted a classic database design challenge: **State that depends on time or relationships cannot be reliably hardcoded into a table column.** If an equipment assignment ends today, a hardcoded `status` column won't magically update to 'Available' tomorrow without a cron job.

To make this a completely "thorough and consistent system," we will shift from static columns to **Dynamic Computed Views**. 

## The Strategy: SQL Views + Manual Overrides
We will use SQL Views to dynamically compute the real-time status of Workers and Equipment. 
- **Manual States** (like `On Leave`, `Maintenance`, `Retired`) will be preserved in the base table.
- **Dynamic States** (like `Assigned`, `In Use`, `Available`) will be computed on-the-fly based on active assignments in `project_tasks` and `equipment_assignments`.

This guarantees that a worker can **never** be labeled "Assigned" unless they actually have an ongoing task.

## Proposed Changes

### 1. Database Schema (`database/schema.sql`)
Create two new SQL Views:

**`worker_status_view`**:
```sql
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
```

**`equipment_status_view`**:
```sql
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
```

### 2. Form Constraints (The UI)
We will modify the Add/Edit forms for Workers and Equipment so that users **cannot** manually select `Assigned` or `In Use`. 
- **Worker Form**: Only allows selecting `Available`, `On Leave`, or `Inactive`.
- **Equipment Form**: Only allows selecting `Available`, `Maintenance`, or `Retired`.
The system will automatically compute `Assigned`/`In Use` when assignments are created.

### 3. Backend Routes
- Update `routes/workers.py` to query from `worker_status_view` and use `computed_status` for display logic.
- Update `routes/equipment.py` to query from `equipment_status_view` and use `computed_status` for display logic.
- Update `routes/projects.py` to query the computed statuses for the project views.

## Verification Plan
1. Rebuild the database to apply the views. The 13 inconsistencies found earlier will instantly disappear.
2. Edit a worker in the UI. Ensure "Assigned" is not an option.
3. Assign an "Available" worker to a task. Watch their status instantly update to "Assigned" on the workers list.

*(Note: We will implement this consistency engine first before proceeding to the Materials module).*
