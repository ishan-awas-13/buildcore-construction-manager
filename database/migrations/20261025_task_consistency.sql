-- ====================================================================
-- BuildCore Database Migration: Task Status & Progress Consistency
-- Target Database: buildcore_copy
-- Date: 2026-10-25
-- ====================================================================

BEGIN;

-- 1. Reconcile existing data violations before applying constraints:
-- Synchronize tasks with 100% progress to 'Completed' status (e.g. Tasks 24, 25 in Project 7)
UPDATE project_tasks 
SET status = 'Completed' 
WHERE completion_percentage = 100 AND status != 'Completed';

-- Synchronize any tasks marked 'Completed' to 100% completion (e.g. Task 26 in Project 8)
UPDATE project_tasks 
SET completion_percentage = 100 
WHERE status = 'Completed' AND completion_percentage != 100;

-- Synchronize any 'Not Started' tasks to 0% completion
UPDATE project_tasks 
SET completion_percentage = 0 
WHERE status = 'Not Started' AND completion_percentage != 0;

-- 2. Add CHECK constraints enforcing status and completion_percentage consistency:
-- A task is 'Completed' if and only if completion_percentage is exactly 100.
ALTER TABLE project_tasks
ADD CONSTRAINT check_task_completion_status
CHECK (
    (status = 'Completed' AND completion_percentage = 100) OR
    (status != 'Completed' AND completion_percentage < 100)
);

-- A task marked 'Not Started' cannot have positive completion progress.
ALTER TABLE project_tasks
ADD CONSTRAINT check_task_not_started_percentage
CHECK (
    (status != 'Not Started' OR completion_percentage = 0)
);

COMMIT;
