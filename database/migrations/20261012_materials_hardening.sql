-- Migration: 20261012_materials_hardening.sql
BEGIN;

ALTER TABLE material_usage DROP CONSTRAINT IF EXISTS uq_project_material;
ALTER TABLE material_usage ADD CONSTRAINT uq_project_material UNIQUE (project_id, material_id);

COMMIT;
