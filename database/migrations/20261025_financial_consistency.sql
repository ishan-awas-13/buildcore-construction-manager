-- ====================================================================
-- BuildCore Database Migration: Financial Consistency & Snapshot Rates
-- Target Database: buildcore_copy
-- Date: 2026-10-25
-- ====================================================================

BEGIN;

-- 1. Reconcile historical task_workers locked_daily_rate from workers master table
-- (Only backfill records where locked rate was 0.00 or NULL)
UPDATE task_workers tw
SET locked_daily_rate = w.daily_rate
FROM workers w
WHERE tw.worker_id = w.worker_id
  AND (tw.locked_daily_rate IS NULL OR tw.locked_daily_rate = 0);

-- 2. Reconcile historical equipment_assignments locked_hourly_rate from equipment master table
-- (Only backfill records where locked rate was 0.00 or NULL)
UPDATE equipment_assignments ea
SET locked_hourly_rate = e.hourly_rate
FROM equipment e
WHERE ea.equipment_id = e.equipment_id
  AND (ea.locked_hourly_rate IS NULL OR ea.locked_hourly_rate = 0);

-- 3. Enforce rate non-negativity constraints
ALTER TABLE task_workers
ADD CONSTRAINT check_tw_locked_daily_rate_non_neg CHECK (locked_daily_rate >= 0);

ALTER TABLE equipment_assignments
ADD CONSTRAINT check_ea_locked_hourly_rate_non_neg CHECK (locked_hourly_rate >= 0);

COMMIT;
