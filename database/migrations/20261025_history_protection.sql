-- ====================================================================
-- BuildCore Database Migration: History Protection & Deprecations
-- Target Database: buildcore_copy
-- Date: 2026-10-25
-- ====================================================================

BEGIN;

-- Formally document legacy project_workers table in PostgreSQL catalog
COMMENT ON TABLE project_workers IS 'DEPRECATED: Legacy direct project-worker junction table. Active application workflows use task_workers for task-level resource scheduling and locked rate accounting.';

COMMIT;
