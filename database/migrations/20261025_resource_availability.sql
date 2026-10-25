-- ====================================================================
-- BuildCore Database Migration: Resource Availability Views
-- Target Database: buildcore_copy
-- Date: 2026-10-25
-- ====================================================================

BEGIN;

-- Update worker_status_view to only mark workers 'Assigned' if their task
-- is currently 'In Progress' AND today falls within the task's active date range.
-- Workers on future tasks or completed tasks remain available.
CREATE OR REPLACE VIEW worker_status_view AS
SELECT 
    w.worker_id,
    w.name,
    w.role,
    w.skill,
    w.phone,
    w.daily_rate,
    w.status,
    CASE 
        WHEN w.status IN ('On Leave', 'Inactive') THEN w.status
        WHEN EXISTS (
            SELECT 1 
            FROM task_workers tw
            JOIN project_tasks pt ON tw.project_task_id = pt.project_task_id
            WHERE tw.worker_id = w.worker_id
              AND pt.status = 'In Progress'
              AND CURRENT_DATE BETWEEN pt.start_date AND pt.due_date
        ) THEN 'Assigned'
        ELSE 'Available'
    END AS computed_status
FROM workers w;

COMMIT;
